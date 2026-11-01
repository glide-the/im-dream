// [Input] Original browser-dependent tool interfaces inside a fixed local document.
// [Output] MCP App/editor leaf; RN owns Chat, navigation and message submission.
// [Pos] Next document route for ToolResultSurface.native.
import type {Metadata} from 'next';
import ToolResultClient from './client';
export const metadata:Metadata={robots:{index:false,follow:false}};
export default function ToolResultPage(){return <ToolResultClient/>;}
