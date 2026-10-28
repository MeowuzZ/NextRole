"""Validation for the verified portion of the reference resume editor."""
def validate_reference_resume(content, consent=None):
    errors=[]
    basics=content.get('basics',{})
    for key,label in [('name','姓名'),('age','年龄'),('documentType','证件类型'),('documentNumber','证件号码')]:
        if not str(basics.get(key,'')).strip(): errors.append({'field':'basics.'+key,'reason':label+'为必填项'})
    age=str(basics.get('age','')).strip()
    if age and (not age.isdigit() or not 1<=int(age)<=120): errors.append({'field':'basics.age','reason':'年龄需为 1–120 的整数'})
    for i,project in enumerate(content.get('projects',[])):
        if not isinstance(project,dict) or not str(project.get('projectName','')).strip(): errors.append({'field':f'projects.{i}.projectName','reason':'请填写项目名称'})
    return errors

# The complete local form uses a shared schema with the browser.
import json
from pathlib import Path
_SCHEMA=json.loads((Path(__file__).parent/'web/resume-schema.json').read_text())
_OPTIONS=json.loads((Path(__file__).parent/'web/resume-options.json').read_text())
_validate_v1=validate_reference_resume

def validate_reference_resume(content, consent=None):
    if content.get('editorSchema')!='honor-reference-v2':
        return _validate_v1(content,consent)
    errors=[]
    for section in _SCHEMA:
        key=section['key']
        rows=[content.get('basics',{})] if key=='basics' else content.get(key,[])
        if not isinstance(rows,list) or (section['required'] and not rows):
            errors.append({'field':key,'reason':'请填写'+section['label']});continue
        for i,row in enumerate(rows):
            if not isinstance(row,dict):
                errors.append({'field':key,'reason':section['label']+'格式不正确'});continue
            for field in section['fields']:
                value=row.get(field['key'],'')
                path=f"{key}.{i}.{field['key']}"
                if not isinstance(value,(str,int,float)) or isinstance(value,bool):
                    errors.append({'field':path,'reason':field['label']+'格式不正确'});continue
                if field['required'] and not str(value).strip():
                    errors.append({'field':path,'reason':'请填写'+field['label']})
                if value and field.get('options') and value not in _OPTIONS[field['options']]:
                    errors.append({'field':path,'reason':'请选择有效的'+field['label']})
                if value and field['type']=='photo' and (not str(value).startswith(('data:image/png;base64,','data:image/jpeg;base64,','data:image/webp;base64,')) or len(str(value))>2800000):
                    errors.append({'field':path,'reason':'照片格式或大小不正确'})
    basics=content.get('basics',{})
    age=str(basics.get('age','')) if isinstance(basics,dict) else ''
    if age and (not age.isdigit() or not 1<=int(age)<=120):
        errors.append({'field':'basics.age','reason':'年龄需为 1–120 的整数'})
    return errors
