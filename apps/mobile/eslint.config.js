// https://docs.expo.dev/guides/using-eslint/
//
// This file is committed on purpose. `expo lint` silently bootstraps an
// equivalent config when none exists, which means CI lint rules were decided by
// whatever eslint/eslint-config-expo versions Expo happened to install at run
// time. Keep it in sync with the devDependencies in apps/mobile/package.json.
const { defineConfig } = require('eslint/config');
const expoConfig = require('eslint-config-expo/flat');

module.exports = defineConfig([
  expoConfig,
  {
    ignores: ['dist/*', '.expo/*'],
  },
]);
