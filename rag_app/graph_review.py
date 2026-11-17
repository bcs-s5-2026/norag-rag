"""Prepare seeded graph-triple review files; never generates human judgments."""
import argparse
import json
import random
from pathlib import Path

from .graph_build import atomic_json
from .graph_retrieval import GraphIndex


def prepare(graph_path, output, seed=20261108, count=10):
    index = GraphIndex.load(graph_path); graph=index.graph
    population=sorted(graph['relations'],key=lambda e:e['id'])
    if len(population)<count:
        raise ValueError('Not enough distinct graph triples; do not sample with replacement.')
    if Path(output).exists(): raise ValueError('Review file exists; do not overwrite human work.')
    chosen=random.Random(seed).sample(population,count)
    rows=[]
    for number,edge in enumerate(chosen,1):
        evidence=[]
        for pid in edge['provenance_ids']:
            proof=index.proofs[pid];chunk=index.chunks[proof['chunk_id']]
            evidence.append(dict(provenance=proof,source_passage=chunk['text'],chunk_id=chunk['id'],
                                 source_document=chunk['name'],source_start=chunk['start'],source_end=chunk['end'],source_line=chunk['line']))
        rows.append(dict(number=number,id=edge['id'],subject=index.entities[edge['subject_id']]['label'],
                         relation=edge['relation'],object=index.entities[edge['object_id']]['label'],
                         condition_quote=edge['condition_quote'],evidence=evidence,
                         grade=None,reviewer=None,notes=None))
    result=dict(graph_build_id=graph['build_id'],graph_content_sha256=graph['graph_content_sha256'],
                seed=seed,population=len(population),sample_size=count,
                selection='random.Random(seed).sample(sorted(distinct relation IDs), count), without replacement',
                grading_rules=dict(correct='The source passage validates the entity, relation, direction and any conditions.',
                                   wrong='The source says something else, including a wrong entity, relation or direction.',
                                   unsupported='The source does not state the claimed relationship; inferred or invented.'),
                counts=None,status='awaiting_human_grades',triples=rows)
    atomic_json(output,result)
    markdown=['# Kestrel: ten triples for manual grading','',
              f'Frozen graph `{graph["build_id"]}`; seed {seed}; sample {count} of {len(population)} distinct relations.',
              '','No grades have been assigned. Use correct / wrong / unsupported; record your name and reason.',
              'Context-expanded evidence is explicitly labelled; the original model quote is preserved. Read the whole source passage.', '']
    for row in rows:
        markdown += [f'## {row["number"]}. {row["subject"]} → {row["relation"]} → {row["object"]}',
                     '',f'Relation ID: `{row["id"]}`',f'Condition: {row["condition_quote"] or "none recorded"}',
                     '','Grade: __________  Reviewer: __________','Reason: __________','']
        for item in row['evidence']:
            proof=item['provenance']
            markdown += [f'Source: `{item["source_document"]}`; chunk `{item["chunk_id"]}`; starting line {item["source_line"]}.',
                         f'Extraction model: `{proof["extraction_model"]}`.','']
            if proof.get('context_heading'):
                markdown += [f'**One endpoint label comes from the section heading:** `{proof["context_heading"]}`', '']
            if 'derivation' in proof:
                markdown += ['**Offline source-context expansion; original response remains quarantined.**','']
            markdown += ['Supporting quotation:','', '````text',proof['quote'],'````','',
                         'Exact full source chunk:','', '````text',item['source_passage'],'````','']
    Path(output).with_suffix('.md').write_text('\n'.join(markdown),encoding='utf-8')
    # Blank grading sheet for the human reviewer. Nothing is pre-filled.
    import csv
    with Path(output).with_name(Path(output).stem+'-GRADES.csv').open('x',newline='',encoding='utf-8') as stream:
        w=csv.writer(stream);w.writerow(['number','subject','relation','object','grade (correct/wrong/unsupported)','reason','reviewer'])
        for row in rows: w.writerow([row['number'],row['subject'],row['relation'],row['object'],'','',''])
    return result


def collect(output):
    """Read the reviewer's filled-in CSV and record it. Refuses blanks or unknown grades;
    it never assigns a grade itself."""
    import csv
    from datetime import datetime, timezone
    output=Path(output); data=json.loads(output.read_text(encoding='utf-8'))
    sheet=output.with_name(output.stem+'-GRADES.csv')
    with sheet.open(newline='',encoding='utf-8-sig') as stream:
        filled={int(r['number']):r for r in csv.DictReader(stream)}
    allowed={'correct','wrong','unsupported'}; counts=dict(correct=0,wrong=0,unsupported=0)
    for row in data['triples']:
        r=filled.get(row['number']) or {}
        grade=(r.get('grade (correct/wrong/unsupported)') or r.get('grade') or '').strip().lower()
        if grade not in allowed or not (r.get('reason') or '').strip() or not (r.get('reviewer') or '').strip():
            raise ValueError(f'Triple {row["number"]}: grade, reason and reviewer are required in {sheet.name}.')
        row.update(grade=grade,notes=r['reason'].strip(),reviewer=r['reviewer'].strip()); counts[grade]+=1
    data.update(counts=counts,status='human_review_complete',
                human_review=dict(method=f'Grades and reasons typed by the reviewer in {sheet.name}; collected verbatim.',
                                  collected_at=datetime.now(timezone.utc).isoformat()))
    graded=output.with_name(output.stem.replace('-ungraded','')+'.json')
    atomic_json(graded,data)
    return graded,counts


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',nargs='?',choices=['prepare','collect'],default='prepare')
    parser.add_argument('--graph-path',type=Path,default=Path('concepts/kestrel_graph_v2/graph.json'))
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--seed',type=int,default=20261108)
    args=parser.parse_args()
    if args.command=='collect':
        graded,counts=collect(args.output); print(f'Recorded your grades in {graded}: {counts}'); return
    result=prepare(args.graph_path,args.output,args.seed)
    print(f"Prepared {result['sample_size']} ungraded triples; population {result['population']}.")


if __name__=='__main__': main()
