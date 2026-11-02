// [Input] A user-selected link and its optional existing local origin.
// [Output] System URL handoff with a bound Linking receiver and rejected-Promise error delivery.
// [Pos] Shared native external-link action; HTTP(S) opens through the system browser handler.
import {Linking} from 'react-native';

export async function openExternalLink(url:string, origin?:string):Promise<void> {
  const target=origin?new URL(url,origin).href:url;
  await Linking.openURL(target);
}
