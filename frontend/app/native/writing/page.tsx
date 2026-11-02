// [Input] Local Writing editor document client boundary.
// [Output] Fixed document route with indexing disabled.
// [Pos] Local editor resource; RN owns application navigation.
import type {Metadata} from 'next';
import WritingDocument from './client';
export const metadata:Metadata={robots:{index:false,follow:false}};
export default function WritingDocumentPage(){return <WritingDocument/>;}
