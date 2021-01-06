const path = require('path');
var CopyWebpackPlugin = require('copy-webpack-plugin');

module.exports = (env, args) => {
    console.log("env:", env, args);
    return {
        entry: {
            index:'./js/index.js',
        },
        target: 'web',
        devtool: (args.mode == "production") ? false : 'inline-source-map',
        node: {
            __dirname: false,
            __filename: false,
        },

        output: {
            filename: '[name].bundle.js',
            path: path.resolve(__dirname, 'dist'),
        },

        module: {
            rules: [
                {
                    test: /\.ts(x?)$/,
                    exclude: /node_modules/,
                    use: [
                        {
                            loader: "ts-loader",
                            options: {
                                transpileOnly: true,
                                experimentalWatchApi: true,
                            },
                        },
                    ]
                },
                {
                    test: /\.(js|jsx)$/,
                    exclude: /node_modules/,
                    use: [
                        {
                            loader: "babel-loader",
                            options: {
                                presets: ['@babel/preset-env', '@babel/preset-react']
                            }
                        },

                    ]
                },
                {
                    test: /antd\.css$/,
                    use: [ 'style-loader', 'css-loader' ]
                },

                {
                    test: [/app\.less$/, /login\.less$/],
                    use: [ 
                        {
                            loader:'style-loader',
                        },
                        {
                            loader:'css-loader',
                            options: {
                                url:false,
                            }
                        },
                        {
                            loader:'less-loader'
                        } 
                    ],
                },

                {
                    test: /\.less$/,
                    exclude: [/app\.less$/, /login\.less$/],
                    use: [ 
                        {
                            loader:'style-loader',
                        },
                        {
                            loader:'css-loader',
                            options: {
                                url:false,
                                importLoaders: 1,
                                modules: true,
                                sourceMap: false,
                                localIdentName: "[name]__[local]___[hash:base64:5]"  // 为了生成类名不是纯随机
                            },
                        },
                        {
                            loader:'less-loader'
                        } 
                    ],
                },


                //todo more test, maybe chrome bug
                // All output '.js' files will have any sourcemaps re-processed by 'source-map-loader'.
                // {
                //     enforce: "pre",
                //     test: /\.js$/,
                //     loader: "source-map-loader"
                // },
            ]
        },

        externals: [
        ],

        resolve: {
            // Add `.ts` and `.tsx` as a resolvable extension.
            extensions: ['.ts', '.tsx', '.js'],
        },

        plugins: [
            new CopyWebpackPlugin({patterns:[
                {from:"index.html", to:"index.html"}
            ]}), 
        ],
    }
};

// module.exports = (env, argv) => {
//     if (argv.mode == "development") {
//         config.module.rules[0].use[0].options.transpileOnly = true;
//     } else if (argv.mode == "production") {
//         config.module.rules[0].use[0].options.transpileOnly = false;
//     }
//     return config;
// };
