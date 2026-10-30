// [Input] Original ordered PNG URLs and the original export filename.
// [Output] Single stitched PNG or original numbered fallback parts, with explicit object-URL ownership.
// [Pos] Browser image preparation shared by original downloads and the narrow native export document.
import type {RenderedThreadImage} from './exportThreadImage';
export interface ThreadImageDownloadArtifact {href:string;fileName:string;owned:boolean;}
export async function prepareThreadImageDownload(rendered:RenderedThreadImage):Promise<ThreadImageDownloadArtifact[]> {
  if(rendered.images.length===1)return [{href:rendered.images[0],fileName:rendered.fileName,owned:false}];
  try {
    const {stitchPngPartsToBlob}=await import('../../lib/png-stitch');
    const blob=await stitchPngPartsToBlob(rendered.images);
    return [{href:URL.createObjectURL(blob),fileName:rendered.fileName,owned:true}];
  }catch {
    const dotIndex=rendered.fileName.lastIndexOf('.');
    const base=dotIndex>0?rendered.fileName.slice(0,dotIndex):rendered.fileName;
    const ext=dotIndex>0?rendered.fileName.slice(dotIndex):'.png';
    return rendered.images.map((href,index)=>({href,fileName:`${base}-part-${index+1}-of-${rendered.images.length}${ext}`,owned:false}));
  }
}
