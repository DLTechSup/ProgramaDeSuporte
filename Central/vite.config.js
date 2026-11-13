import react from '@vitejs/plugin-react';

export default {
  root: 'src/renderer',
  base: './',
  plugins: [react()],
  build: { outDir: '../../dist', emptyOutDir: true },
};
