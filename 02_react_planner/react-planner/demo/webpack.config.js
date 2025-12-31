const path = require('path');
const HtmlWebpackPlugin = require('html-webpack-plugin');

module.exports = (env = {}, argv = {}) => {
  const mode = argv.mode || 'development';
  const isProd = mode === 'production';

  return {
    mode,
    entry: path.resolve(__dirname, './src/renderer.tsx'),
    output: {
      path: path.resolve(__dirname, './dist'),
      filename: isProd ? '[name].[contenthash].js' : 'app.js',
      chunkFilename: isProd ? '[name].[contenthash].js' : '[name].js',
      publicPath: '/'
    },
    resolve: {
      extensions: ['.ts', '.tsx', '.js', '.jsx'],
      alias: {
        // Resolve package name to local repo source when running demo inside this repo
        '@archef2000/react-planner': path.resolve(__dirname, '../src')
      }
    },
    module: {
      rules: [
        {
          test: /\.(ts|tsx)$/,
          use: 'ts-loader',
          exclude: /node_modules/
        },
        {
          test: /\.(png|jpg|jpeg|gif)$/i,
          type: 'asset/resource'
        },
        // Demo catalog uses Blender assets (.obj/.mtl)
        {
          test: /\.(obj|mtl)$/i,
          type: 'asset/source'
        }
      ]
    },
    plugins: [
      new HtmlWebpackPlugin({
        template: path.resolve(__dirname, './src/index.html.ejs')
      })
    ],
    devtool: isProd ? false : 'inline-source-map',
    devServer: {
      port: 5173,
      hot: true,
      historyApiFallback: true,
      client: {
        webSocketURL: 'ws://localhost:5173/ws'
      },
      setupMiddlewares: (middlewares, devServer) => {
        if (devServer && devServer.app) {
          devServer.app.use((req, res, next) => {
            res.setHeader('Cache-Control', 'no-store');
            next();
          });
        }
        return middlewares;
      }
    }
  };
};
