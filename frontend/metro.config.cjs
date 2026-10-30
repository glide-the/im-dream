// [Input] Unified frontend source and platform-specific RN modules.
// [Output] Metro native resolution with a native-only Babel transformer.
// [Pos] Native build configuration; Next owns the Web build.
const {getDefaultConfig, mergeConfig} = require('@react-native/metro-config');
module.exports = mergeConfig(getDefaultConfig(__dirname), {
  maxWorkers: 2,
  transformer: {babelTransformerPath: require.resolve('./scripts/native-babel-transformer.cjs')},
  resolver: {blockList: [/\/legacy\//, /\/ios\//, /\/android\//, /\/\.next\//]},
});
