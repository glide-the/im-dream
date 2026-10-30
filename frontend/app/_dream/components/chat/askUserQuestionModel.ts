// [Input] Original AskUserQuestion tool input and the active translation function.
// [Output] Unchanged question fields, option/default semantics and answer keys.
// [Pos] Shared normalization only; UI and canonical confirmation submission remain caller-owned.
import type {TFunction} from 'i18next';
import type {QuestionOption} from './askUserQuestionAnswers';
export interface QuestionField {
  id?:string;question?:string;label?:string;header?:string;
  type?:'text'|'textarea'|'select'|'checkbox'|'radio'|'number';options?:QuestionOption[];
  required?:boolean;default?:string|number|boolean|string[];placeholder?:string;description?:string;multiSelect?:boolean;
}
export interface AskUserQuestionInput {
  questions?:QuestionField[];question?:string;message?:string;text?:string;prompt?:string;options?:string[];choices?:string[];default?:string;
}
export function normalizeAskUserQuestions(input:AskUserQuestionInput|undefined,t:TFunction):QuestionField[] {
  if(!input)return [{id:'answer',question:t('chat.askUser.fallbackQuestion'),type:'text',required:true}];
  if(input.questions?.length)return input.questions.map((question,index)=>({
    id:question.id || `q${index}`,
    question:question.question || question.label || question.header || t('chat.askUser.questionNumber',{number:index+1}),
    type:question.type || (Array.isArray(question.options) && question.options.length>0?'radio':'text'),
    options:question.options,required:question.required ?? true,default:question.default,placeholder:question.placeholder,description:question.description,multiSelect:question.multiSelect,
  }));
  const question=input.question || input.message || input.text || input.prompt;
  if(question){const options=input.options || input.choices;return [{id:'answer',question,type:options?.length?'radio':'text',options,required:true,default:input.default}];}
  return [{id:'answer',question:t('chat.askUser.fallbackQuestion'),type:'text',required:true}];
}
