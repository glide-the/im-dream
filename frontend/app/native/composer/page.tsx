// [Input] Original rich editor document for an embedded native composer.
// [Output] Editor-only client content; public business APIs and the normal Web shell retain their owners.
// [Pos] Fixed local document route consumed by MarkdownInputEditor.native.tsx.
import type {Metadata} from 'next';
import MarkdownInputDocument from '../../_dream/components/chat/MarkdownInputDocument';
export const metadata:Metadata={robots:{index:false,follow:false}};
export default function ComposerDocumentPage() {return <MarkdownInputDocument />;}
