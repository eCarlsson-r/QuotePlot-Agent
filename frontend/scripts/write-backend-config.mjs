import { writeFile } from 'node:fs/promises';

const backendOrigin = (process.env.QUOTE_PLOT_BACKEND_ORIGIN || '').replace(/\/+$/, '');
const network = (process.env.QUOTE_PLOT_NETWORK || 'sepolia').trim();
const networkSettings = {
  sepolia: {
    chainId: 11155111,
    rpcUrl: process.env.QUOTE_PLOT_SEPOLIA_RPC_URL || 'https://ethereum-sepolia-rpc.publicnode.com',
  },
  bscTestnet: {
    chainId: 97,
    rpcUrl: process.env.QUOTE_PLOT_BSC_TESTNET_RPC_URL || 'https://bsc-testnet-dataseed.bnbchain.org',
  },
};

if (!(network in networkSettings)) {
  throw new Error('QUOTE_PLOT_NETWORK must be either sepolia or bscTestnet.');
}

const { chainId, rpcUrl } = networkSettings[network];
const factoryAddress = (process.env.QUOTE_PLOT_FACTORY_ADDRESS || '').trim();

if (backendOrigin) {
  const url = new URL(backendOrigin);
  const allowedProtocol = url.protocol === 'https:' ||
    (url.protocol === 'http:' && ['localhost', '127.0.0.1'].includes(url.hostname));
  if (!allowedProtocol || url.pathname !== '/' || url.search || url.hash) {
    throw new Error('QUOTE_PLOT_BACKEND_ORIGIN must be an HTTPS origin (HTTP is allowed for localhost only).');
  }
}

const parsedRpcUrl = new URL(rpcUrl);
const allowedRpcProtocol = parsedRpcUrl.protocol === 'https:' ||
  (parsedRpcUrl.protocol === 'http:' && ['localhost', '127.0.0.1'].includes(parsedRpcUrl.hostname));
if (!allowedRpcProtocol || parsedRpcUrl.search || parsedRpcUrl.hash) {
  throw new Error('The configured frontend RPC URL must use HTTPS (HTTP is allowed for localhost only), without query or fragment.');
}

if (factoryAddress && !/^0x[\da-fA-F]{40}$/.test(factoryAddress)) {
  throw new Error('QUOTE_PLOT_FACTORY_ADDRESS must be a 20-byte EVM address.');
}

if (network === 'bscTestnet' && !factoryAddress) {
  throw new Error('QUOTE_PLOT_FACTORY_ADDRESS is required when QUOTE_PLOT_NETWORK=bscTestnet.');
}

const config = `window.__QUOTE_PLOT_CONFIG__ = ${JSON.stringify({ backendOrigin, network, chainId, rpcUrl, factoryAddress })};\n`;
await writeFile(new URL('../public/quoteplot-config.js', import.meta.url), config);
