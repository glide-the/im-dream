// [Input] Original Writing display DTOs plus chooser presentation and single-use open intents.
// [Output] Strict protocol validation for loading, nullable state, revisions and malformed payloads.
// [Pos] Provider-free protocol tests; host URL/document/revision ownership is also exercised in the native frame browser fixture.
import {expect,test} from '@playwright/test';
import {readWritingEvent,readWritingState} from '../Editor/WritingDocument.protocol';
const state={type:'state',documentId:'writing-document',revision:1,active:true,theme:'light',language:'en',showEnergyBar:true};
const view={type:'chooser-view',documentId:'writing-document',revision:1,loading:false,selectedStateId:'happy',name:'Happy',expanded:false};
test('the original state DTO accepts an optional positive safe open nonce only',()=>{
 expect(readWritingState(state)).toEqual(state);
 expect(readWritingState({...state,openChooserNonce:1})).toMatchObject({openChooserNonce:1});
 for(const nonce of [0,-1,1.5,'1',NaN,Infinity,Number.MAX_SAFE_INTEGER+1,null])expect(readWritingState({...state,openChooserNonce:nonce})).toBeNull();
});
test('chooser presentation requires every field and a positive safe revision',()=>{
 expect(readWritingEvent(JSON.stringify(view))).toEqual(view);
 expect(readWritingEvent(JSON.stringify({...view,selectedStateId:null,loading:true,name:''}))).toMatchObject({selectedStateId:null,loading:true});
 for(const change of [{revision:0},{revision:1.5},{revision:'1'},{loading:'false'},{expanded:0},{selectedStateId:{}},{name:null},{documentId:4}])expect(readWritingEvent(JSON.stringify({...view,...change}))).toBeNull();
 for(const key of ['revision','loading','selectedStateId','name','expanded']){const raw:any={...view};delete raw[key];expect(readWritingEvent(JSON.stringify(raw))).toBeNull();}
 for(const raw of ['null','[]','invalid'])expect(readWritingEvent(raw)).toBeNull();
});
