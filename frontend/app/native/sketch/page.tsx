// [Input] The original browser sketch dialog and the fixed native document bridge.
// [Output] A local sketch-only document with no session bootstrap, business API or application navigation.
// [Pos] Native complex-editor leaf route; original Web Chat continues to render its existing dialog.
import type {Metadata} from 'next';
import SketchInputDocument from '../../_dream/components/chat/SketchInputDocument';
export const metadata:Metadata={robots:{index:false,follow:false}};
export default function SketchDocumentPage(){return <SketchInputDocument />;}
