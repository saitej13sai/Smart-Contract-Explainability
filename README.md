# Smart-Contract-Explainability
A Python CLI tool that generates plain-English summaries of Ethereum smart contracts, using web3.py to fetch contract ABIs from the Sepolia testnet and OpenAI's API for analysis. It accepts either a contract address or raw Solidity code as input and outputs a summary of the contract's purpose, key functions, permissions, and security patterns.

Features

Analyzes Sepolia testnet contract addresses or raw Solidity code.
Fetches contract ABIs via Etherscan API.
Generates summaries covering:
Contract purpose and functionality.
Key functions and their roles.
Permissions and access control.
Security patterns and potential risks.
Includes input validation and error handling.
