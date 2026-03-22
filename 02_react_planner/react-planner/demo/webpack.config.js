const path = require('path');
const HtmlWebpackPlugin = require('html-webpack-plugin');

module.exports = {
  mode: 'development',

  entry: path.resolve(__dirname, './src/renderer.tsx'),

  output: {
    path: path.resolve(__dirname),
    filename: 'app.js',
    publicPath: '/',
    clean: false,
  },

  resolve: {
    extensions: ['.ts', '.tsx', '.js', '.jsx', '.json'],
    alias: {
      '@archef2000/react-planner': path.resolve(__dirname, '../src'),
    },
  },

  module: {
    rules: [
      {
        test: /\.[jt]sx?$/,
        exclude: /node_modules/,
        use: {
          loader: 'ts-loader',
          options: {
            transpileOnly: true,
          },
        },
      },
      {
        test: /\.(png|jpe?g|gif|svg|webp)$/i,
        type: 'asset/resource',
      },
      {
        test: /\.(woff2?|eot|ttf|otf)$/i,
        type: 'asset/resource',
      },
      {
        test: /\.css$/i,
        use: ['style-loader', 'css-loader'],
      },
      {
        test: /\.(obj|mtl)$/i,
        type: 'asset/source',
      },
    ],
  },

  plugins: [
    new HtmlWebpackPlugin({
      template: path.resolve(__dirname, './src/index.html.ejs'),
    }),
  ],

  devtool: 'eval-source-map',

  devServer: {
    port: 5173,
    hot: true,
    historyApiFallback: true,
    static: {
      directory: path.resolve(__dirname, './public'),
      publicPath: '/',
    },
    client: {
      overlay: true,
      logging: 'info',
    },
    setupMiddlewares: (middlewares) => {
      return middlewares;
    },
  },
};