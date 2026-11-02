// [Input] RN app sources and the locked native dependency graph.
// [Output] Standalone iOS JavaScript bundle; business pages remain in Next.
// [Pos] RN Metro entry.
const {getDefaultConfig, mergeConfig} = require('@react-native/metro-config');
module.exports = mergeConfig(getDefaultConfig(__dirname), {maxWorkers: 2});
