// [Input] Metro modules with native JSX/TypeScript syntax.
// [Output] RN Babel transform isolated from the Next/SWC configuration.
// [Pos] Native compiler adapter.
const babel = require('@babel/core');
exports.transform = ({src, filename}) => ({
  ast: babel.transformSync(src, {
    filename, ast: true, code: false, babelrc: false, configFile: false,
    presets: [require.resolve('@react-native/babel-preset')],
  }).ast,
});
