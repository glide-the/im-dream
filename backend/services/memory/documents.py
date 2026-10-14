# [Input] Frozen persisted report results and exact source metadata.
# [Output] UTF-8 L2/L3 documents, digests and compound expression classification.
# [Pos] Deterministic memory conversion; observations do not become personal facts.
# [Sync] 2026-10-15: source-preserving converter and fixed published taxonomy.
from __future__ import annotations
from hashlib import sha256
import json
from pathlib import Path
import re
from services.admin_data.memory_data import ArtifactDTO, SourceDTO, MetadataDTO

POLICY=json.loads(Path(__file__).with_name('policy.json').read_text())
REVISION=POLICY['revision']
THEMES={t['id']:t for t in POLICY['themes']}
TAG_THEME={tag:t['id'] for t in POLICY['themes'] for tag in t['tags']}
def digest(text: str) -> str: return sha256(text.encode('utf-8')).hexdigest()
def encode(header: dict, title: str, records: list) -> tuple[str,str]:
    body=f'# {title}\n\n```json\n'+json.dumps(records,ensure_ascii=False,indent=2)+'\n```\n'
    body_sha=digest(body)
    header={**header,'body_sha256':body_sha}
    return '---\n'+json.dumps(header,ensure_ascii=False,sort_keys=True,indent=2)+'\n---\n'+body,body_sha

def decode(document: str) -> tuple[dict,list]:
    if not document.startswith('---\n'): raise ValueError('MEMORY_DOCUMENT_INVALID')
    header_text,body=document[4:].split('\n---\n',1)
    header=json.loads(header_text)
    if header.get('body_sha256')!=digest(body): raise ValueError('MEMORY_DOCUMENT_INVALID')
    start=body.index('```json\n')+len('```json\n')
    records=json.loads(body[start:body.rindex('\n```')])
    if not isinstance(records,list): raise ValueError('MEMORY_DOCUMENT_INVALID')
    return header,records

def classify(text: str) -> list[str]:
    if any(re.search(POLICY[key],text,re.I) for key in ('excluded_expression','explicit_boundary','negated_expression')): return []
    return [tag for tag,pattern in POLICY['tag_patterns'].items() if re.search(pattern,text,re.I)]

def convert(source:SourceDTO, artifact:ArtifactDTO):
    records=[];by_text={};completed=list(source.completed_sections)
    for section in ('echoes','traits','patterns'):
        values=getattr(source,section)
        if section not in source.completed_sections: continue
        for item in values:
            if not item.description.strip(): continue
            source_ref={'result_id':item.id,'section':section,'related_session_ids':item.related_session_ids,'evidence':item.evidence,'confidence':item.confidence}
            key=(item.title.strip(),item.description.strip())
            if key in by_text:
                by_text[key]['sources'].append(source_ref);continue
            row={'item_id':item.id,'title':item.title,'observation':item.description,'evidence_kind':'analysis_inference','observation_period':{'start_date':source.start_date,'end_date':source.end_date,'report_created_at':source.created_at},'sources':[source_ref]}
            records.append(row);by_text[key]=row
    metadata=MetadataDTO(task_id=source.task_id,report_id=source.report_id,completed_sections=completed,failed_sections=source.failed_sections,item_count=len(records),theme_count=0)
    if not records: return None,None,None,metadata
    header={'schema_version':1,'artifact_id':artifact.artifact_id,'revision':artifact.revision,'report_id':source.report_id,'task_id':source.task_id,'source_sha256':artifact.source_sha256,'report_digest':source.report_sha256,'analysis_content':source.analysis_content.model_dump() if source.analysis_content is not None else None,'conversion_revision':REVISION,'execution_mode':POLICY['execution_mode'],'model_id':None,'thread_id':None,'turn_id':None,'completed_sections':completed,'failed_sections':source.failed_sections,'observation_period':{'start_date':source.start_date,'end_date':source.end_date,'report_created_at':source.created_at}}
    l2,body_sha=encode(header,'Reflections 记忆蒸馏',records)
    l3=None
    try:
        l3,theme_count=convert_theme(source,artifact,header,records,body_sha)
    except (ValueError,TypeError,KeyError,re.error):
        l3,theme_count=None,0
    metadata=metadata.model_copy(update={'theme_count':theme_count})
    return l2,body_sha,l3,metadata

def convert_theme(source,artifact,header,records,body_sha):
    themes=[]
    for row in records:
        expressions=[row['observation'],*(s['evidence'] for s in row['sources'])]
        tag_excerpts={}
        for text in expressions:
            for tag in classify(text): tag_excerpts.setdefault(tag,text)
        for tag,excerpt in tag_excerpts.items():
            theme=TAG_THEME[tag]
            themes.append({'theme_record_id':digest(row['item_id']+tag),'THEME':theme,'Focus':row['title'],'Polarity':None,'Attribution':None,'TriggeringConditions':excerpt,'TriggeringTagId':tag,'source_distillation_id':artifact.artifact_id,'source_distillation_revision':artifact.revision,'source_body_sha256':body_sha,'taxonomy_revision':REVISION,'source_item_ids':[row['item_id']],'source_excerpt':excerpt,'evidence_kind':'analysis_inference','observation_period':row['observation_period']})
    l3,_=encode({**header,'source_distillation_id':artifact.artifact_id,'source_distillation_revision':artifact.revision,'source_body_sha256':body_sha,'taxonomy_revision':REVISION},'Reflections 记忆主题',themes)
    return l3,len(themes)

def validate_document(artifact:ArtifactDTO, *, theme=False):
    document=artifact.theme_document if theme else artifact.document
    expected_sha=artifact.theme_sha256 if theme else artifact.document_sha256
    if document is None or expected_sha is None: raise ValueError('MEMORY_DOCUMENT_UNAVAILABLE')
    if digest(document)!=expected_sha: raise ValueError('MEMORY_DOCUMENT_INVALID')
    header,records=decode(document)
    for k,v in {'artifact_id':artifact.artifact_id,'revision':artifact.revision,'report_id':artifact.report_id,'source_sha256':artifact.source_sha256,'conversion_revision':REVISION}.items():
        if header.get(k)!=v: raise ValueError('MEMORY_SOURCE_MISMATCH')
    if theme:
        if header.get('source_body_sha256')!=artifact.body_sha256 or header.get('taxonomy_revision')!=REVISION: raise ValueError('MEMORY_SOURCE_MISMATCH')
        _,l2_records=validate_document(artifact)
        l2_items={item['item_id']:item for item in l2_records}
        for row in records:
            source_ids=row.get('source_item_ids',[])
            if not source_ids or any(i not in l2_items for i in source_ids): raise ValueError('MEMORY_SOURCE_MISMATCH')
            expressions=[v for i in source_ids for v in [l2_items[i]['observation'],*(s['evidence'] for s in l2_items[i]['sources'])]]
            if row.get('source_excerpt') not in expressions or row.get('TriggeringConditions')!=row.get('source_excerpt') or row.get('evidence_kind')!='analysis_inference': raise ValueError('MEMORY_SOURCE_MISMATCH')
            if row.get('TriggeringTagId') not in TAG_THEME or TAG_THEME[row['TriggeringTagId']]!=row.get('THEME') or row.get('source_distillation_revision')!=artifact.revision or row.get('source_distillation_id')!=artifact.artifact_id: raise ValueError('MEMORY_THEME_INVALID')
    elif header.get('body_sha256')!=artifact.body_sha256 or len(document.encode())!=artifact.byte_length:
        raise ValueError('MEMORY_DOCUMENT_INVALID')
    return header,records
