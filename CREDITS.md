# Third-Party Licenses and Credits

## Local AI Models Used

### Qwen2.5-VL (Default)
- **License**: Apache-2.0
- **Source**: Alibaba Cloud
- **Usage**: Multimodal invoice parsing (images → JSON)
- **License File**: `THIRD_PARTY_LICENSES/Qwen2.5-VL-LICENSE.txt`

### Llama 3.1 (Optional)
- **License**: Llama Community License
- **Source**: Meta AI
- **Usage**: Text-only invoice parsing (when used with Surya)
- **License File**: `THIRD_PARTY_LICENSES/Llama-Community-License.txt`

### Surya (Optional)
- **License**: Apache-2.0
- **Source**: VikParuchuri/surya
- **Usage**: Layout analysis and table extraction
- **License File**: `THIRD_PARTY_LICENSES/Surya-LICENSE.txt`

## OCR Fallback

### PaddleOCR
- **License**: Apache-2.0
- **Source**: PaddlePaddle
- **Usage**: OCR fallback when local LLM is unavailable

## Attribution

Document parsing powered by local models: Qwen2.5-VL (Apache-2.0). Optional adapter: Llama (Community License). 