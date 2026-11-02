// [Input] Original DOM long-image renderer and the fixed native share bridge.
// [Output] A capture-only local document without the application shell or business endpoints.
// [Pos] Narrow native export leaf; original Web Chat retains its existing share dialog.
import type {Metadata} from 'next';
import ChatImageDocument from '../../_dream/components/chat/ChatImageDocument';
export const metadata:Metadata={robots:{index:false,follow:false}};
export default function ChatExportDocumentPage(){return <ChatImageDocument/>;}
