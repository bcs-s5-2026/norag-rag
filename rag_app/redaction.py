"""V4 Part C: personal data redaction with patterns (email addresses, phone numbers).

Each detected value is replaced by a placeholder such as [EMAIL_1] before the
text is sent to the LLM provider or written to a trace. The mapping stays in
memory for the current request only, so the answer can be restored locally.
Names are NOT detected: a pattern cannot tell a person's name from other words.
"""
import re

EMAIL = re.compile(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+')
# A phone candidate: digits with the usual separators, not glued to a word or
# to a decimal part. A full stop ending the sentence after the number is allowed.
PHONE = re.compile(r'(?<!\w)(?<!\d\.)\+?\(?\d[\d ().-]{7,}\d(?!\w)(?!\.\d)')
IP_ADDRESS = re.compile(r'\d{1,3}(\.\d{1,3}){3}')
ISO_DATE = re.compile(r'\d{4}-\d{2}-\d{2}')
DECIMAL = re.compile(r'\d+\.\d+')


def is_phone(value):
    """Keep only candidates that look like a phone number (9 to 15 digits)."""
    digits = sum(character.isdigit() for character in value)
    if not 9 <= digits <= 15:
        return False
    if IP_ADDRESS.fullmatch(value) or DECIMAL.fullmatch(value):
        return False
    return not ISO_DATE.search(value)


class Redactor:
    """One instance per request: the same value always gets the same placeholder."""

    def __init__(self):
        self.originals = {}     # placeholder -> original value
        self.placeholders = {}  # original value -> placeholder

    def _placeholder(self, kind, value):
        if value not in self.placeholders:
            number = sum(name.startswith(f'[{kind}_') for name in self.originals) + 1
            name = f'[{kind}_{number}]'
            self.placeholders[value] = name
            self.originals[name] = value
        return self.placeholders[value]

    def redact(self, text):
        text = EMAIL.sub(lambda match: self._placeholder('EMAIL', match.group()), text)
        return PHONE.sub(lambda match: self._placeholder('PHONE', match.group())
                         if is_phone(match.group()) else match.group(), text)

    def restore(self, text):
        for name, value in self.originals.items():
            text = text.replace(name, value)
        return text

    def invented(self, text):
        """Addresses or numbers in an LLM answer that were in neither the question nor the evidence.

        Only placeholders were sent, so a real-looking value was written by the model
        itself. If it equals a value we hid, the model guessed right; otherwise it is invented.
        """
        found = EMAIL.findall(text) + [m.group() for m in PHONE.finditer(text) if is_phone(m.group())]
        return [value for value in found if value not in self.placeholders]

    def counts(self):
        return dict(emails=sum(name.startswith('[EMAIL_') for name in self.originals),
                    phones=sum(name.startswith('[PHONE_') for name in self.originals))
