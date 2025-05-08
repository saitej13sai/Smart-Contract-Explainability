import argparse
import os
import json
import requests
from web3 import Web3
from openai import OpenAI

openai_client = OpenAI(api_key=os.getenv("OPENAI API KEY"))

INFURA_URL = f"https://sepolia.infura.io/v3/{os.getenv("INFURA API KEY")}"
w3 = Web3(Web3.HTTPProvider(INFURA_URL))

PROMPT_TEMPLATE = """
You are an expert Solidity developer. Analyze the following smart contract input (either ABI or Solidity code) and provide a plain-English technical summary.

**Input**:
{contract_input}

**Instructions**:
- Summarize the contract's purpose and functionality.
- Identify key functions and their roles.
- Describe permissions and access control (e.g., who can call what).
- Highlight security patterns or potential risks (e.g., use of modifiers, reentrancy protection).
- If the input is invalid or unclear, return an error message.

**Output Format**:
```markdown
## Contract Summary
[Purpose and functionality]

## Key Functions
- [Function name]: [Description and role]

## Permissions
- [Who can call what, e.g., owner-only functions]

## Security Patterns
- [Security measures or risks, e.g., use of OpenZeppelin, checks-effects-interactions]
```

**Example Input** (Solidity):
```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract AllowlistToken is ERC20, Ownable {
    mapping(address => bool) private _allowlist;

    constructor(string memory name, string memory symbol) ERC20(name, symbol) Ownable(msg.sender) {}

    modifier onlyAllowlisted() {
        require(_allowlist[msg.sender], "Not allowlisted");
        _;
    }

    function mint(address to, uint256 amount) external onlyAllowlisted {
        _mint(to, amount);
    }

    function addToAllowlist(address account) external onlyOwner {
        _allowlist[account] = true;
    }
}
```

**Example Output**:
```markdown
## Contract Summary
This is an ERC-20 token contract with minting restricted to addresses in an allowlist, managed by the contract owner.

## Key Functions
- mint(address to, uint256 amount): Mints tokens to a specified address, callable only by allowlisted addresses.
- addToAllowlist(address account): Adds an address to the allowlist, callable only by the owner.

## Permissions
- Only allowlisted addresses can call the mint function.
- Only the contract owner can call addToAllowlist to manage the allowlist.

## Security Patterns
- Uses OpenZeppelin's ERC-20 and Ownable for audited, secure implementations.
- Employs a modifier (onlyAllowlisted) to restrict minting.
- Solidity ^0.8.0 prevents overflow/underflow.
- No reentrancy guards needed as minting does not call external contracts.
```
"""

def parse_abi_to_readable_format(abi):
    functions = []
    for item in abi:
        if item['type'] == 'function':
            inputs = [f"{param['type']} {param.get('name', '')}".strip() for param in item.get('inputs', [])]
            functions.append(f"{item['name']}({', '.join(inputs)})")
    return '\n'.join(functions) if functions else "No functions found in ABI."

def fetch_contract_abi(contract_address):
    try:
        if not w3.is_address(contract_address):
            return None, "Error: Invalid Ethereum address."
        if not w3.is_connected():
            return None, "Error: Failed to connect to Sepolia testnet."
        etherscan_url = (
            f"https://api-sepolia.etherscan.io/api?module=contract&action=getabi"
            f"&address={contract_address}&apikey={os.getenv('ETHERSCAN_API_KEY')}"
        )
        response = requests.get(etherscan_url)
        if response.status_code != 200 or response.json()['status'] != '1':
            return None, "Error: Failed to fetch ABI from Etherscan."
        abi = response.json()['result']
        if abi == 'Contract source code not verified':
            return None, "Error: Contract ABI not available (source code not verified)."
        return json.loads(abi), None
    except Exception as e:
        return None, f"Error: Failed to fetch ABI. Details: {str(e)}"

def generate_contract_summary(input_data, is_address=False):
    try:
        if is_address:
            abi, error = fetch_contract_abi(input_data)
            if error:
                return error
            contract_input = parse_abi_to_readable_format(abi)
        else:
            contract_input = input_data
        prompt = PROMPT_TEMPLATE.format(contract_input=contract_input)
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a Solidity contract analyst."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=1500
        )
        output = response.choices[0].message.content.strip()
        if "## Contract Summary" not in output:
            return "Error: Generated output does not follow the required format."
        return output
    except Exception as e:
        return f"Error: Failed to generate summary. Details: {str(e)}"

def main():
    parser = argparse.ArgumentParser(description="Generate a plain-English summary of a smart contract.")
    parser.add_argument("--address", type=str, help="Sepolia testnet contract address (e.g., 0x123...)")
    parser.add_argument("--code", type=str, help="Raw Solidity code (wrap in quotes or provide file path)")
    args = parser.parse_args()
    if not args.address and not args.code:
        print("Error: Must provide either --address or --code.")
        return
    if args.address and args.code:
        print("Error: You cannot provide both --address and --code. Please choose one.")
        return
    if args.address:
        result = generate_contract_summary(args.address, is_address=True)
        print(result)
    elif args.code:
        if os.path.isfile(args.code):
            with open(args.code, 'r') as f:
                solidity_code = f.read()
        else:
            solidity_code = args.code
        result = generate_contract_summary(solidity_code, is_address=False)
        print(result)

if __name__ == "__main__":
    main()
