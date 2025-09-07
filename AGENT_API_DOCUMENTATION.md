# Agent API Documentation

## ✅ **Implementation Status: COMPLETE**

Successfully implemented the agent API endpoints in `backend/routes/agent.py` and integrated them into the main FastAPI application.

## 📍 **API Endpoints**

### Base URL
```
http://localhost:8000/api/agent
```

## 🔧 **Core Endpoints**

### 1. **POST /api/agent/ask**
Main endpoint for asking the agent questions.

**Request Body:**
```json
{
    "user_prompt": "What should I do about this invoice?",
    "user_id": "user_123",
    "invoice_id": "INV-73318",
    "role": "gm"
}
```

**Response:**
```json
{
    "markdown": "Based on the invoice analysis, I recommend...",
    "actions": [
        {
            "type": "credit_suggestion",
            "description": "Suggested: Credit Suggestion",
            "priority": "medium"
        }
    ],
    "confidence": 85,
    "entities": {
        "suppliers": ["ABC Corporation"],
        "amounts": ["£150.50"],
        "dates": ["15/01/2024"],
        "invoice_numbers": ["INV-73318"],
        "items": ["tomatoes"]
    },
    "urgency": "medium"
}
```

### 2. **POST /api/agent/ask-with-memory**
Enhanced endpoint that includes conversation history for more contextual responses.

**Request Body:** Same as `/ask`

**Response:** Same structure as `/ask` but with conversation-aware responses

### 3. **POST /api/agent/specialized**
Handle specialized agent tasks.

**Request Body:**
```json
{
    "user_prompt": "Suggest a credit for this invoice",
    "user_id": "user_123",
    "invoice_id": "INV-73318",
    "role": "gm",
    "task_type": "credit_suggestion"
}
```

**Supported task_types:**
- `credit_suggestion`
- `email_generation`
- `escalation`
- `price_analysis`

## ⚡ **Convenience Endpoints**

### 4. **POST /api/agent/suggest-credit**
Quick credit suggestion endpoint.

**Request Body:**
```json
{
    "user_id": "user_123",
    "invoice_id": "INV-73318",
    "role": "gm"
}
```

### 5. **POST /api/agent/generate-email**
Quick email generation endpoint.

**Request Body:** Same as suggest-credit

### 6. **POST /api/agent/escalate**
Quick issue escalation endpoint.

**Request Body:** Same as suggest-credit

## 🔍 **Information Endpoints**

### 7. **GET /api/agent/health**
Health check for the agent service.

**Response:**
```json
{
    "status": "healthy",
    "agent_version": "1.0.0",
    "capabilities": ["invoice_analysis", "credit_suggestions", ...],
    "message": "Agent service is operational"
}
```

### 8. **GET /api/agent/capabilities**
Get information about agent capabilities.

**Response:**
```json
{
    "capabilities": [
        "invoice_analysis",
        "credit_suggestions",
        "email_generation",
        "issue_escalation",
        "price_analysis",
        "supplier_insights",
        "role_aware_responses",
        "conversation_memory"
    ],
    "supported_roles": ["gm", "finance", "shift"],
    "supported_tasks": [
        "credit_suggestion",
        "email_generation",
        "escalation",
        "price_analysis"
    ],
    "response_formats": {
        "markdown": "Agent's written response",
        "actions": "Suggested actions for the user",
        "confidence": "Confidence score (0-100)",
        "entities": "Extracted entities (suppliers, amounts, etc.)",
        "urgency": "Urgency level (low, medium, high)"
    }
}
```

## 🎨 **User Roles**

### GM (General Manager)
- Focus on practical actions and cost implications
- Operational decision support
- Cost management guidance

### Finance
- Focus on accuracy and compliance
- Financial analysis and auditing
- Compliance considerations

### Shift
- Focus on immediate operations
- Inventory management
- Daily operational efficiency

## 📊 **Response Fields**

### markdown
The agent's natural language response to the user's question.

### actions
List of suggested actions the user can take:
```json
[
    {
        "type": "credit_suggestion",
        "description": "Suggested: Credit Suggestion",
        "priority": "medium"
    }
]
```

### confidence
Confidence score (0-100) indicating how certain the agent is about its response.

### entities
Extracted entities from the response:
```json
{
    "suppliers": ["ABC Corporation"],
    "amounts": ["£150.50"],
    "dates": ["15/01/2024"],
    "invoice_numbers": ["INV-73318"],
    "items": ["tomatoes"]
}
```

### urgency
Urgency level: `"low"`, `"medium"`, or `"high"`

## 🧪 **Testing**

### Manual Testing with curl

**Test basic agent ask:**
```bash
curl -X POST "http://localhost:8000/api/agent/ask" \
  -H "Content-Type: application/json" \
  -d '{
    "user_prompt": "What should I do about this invoice?",
    "user_id": "test_user_123",
    "invoice_id": "INV-73318",
    "role": "gm"
  }'
```

**Test health check:**
```bash
curl "http://localhost:8000/api/agent/health"
```

**Test capabilities:**
```bash
curl "http://localhost:8000/api/agent/capabilities"
```

### Automated Testing
Run the test script:
```bash
python3 test_agent_api.py
```

## 🔧 **Integration Examples**

### Frontend Integration (JavaScript)
```javascript
// Ask the agent a question
async function askAgent(userPrompt, userId, invoiceId, role) {
    const response = await fetch('/api/agent/ask', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            user_prompt: userPrompt,
            user_id: userId,
            invoice_id: invoiceId,
            role: role
        })
    });
    
    const result = await response.json();
    
    // Display the response
    console.log('Agent response:', result.markdown);
    console.log('Confidence:', result.confidence);
    console.log('Suggested actions:', result.actions);
    
    return result;
}

// Example usage
askAgent(
    "Why is this invoice more expensive than usual?",
    "user_123",
    "INV-73318",
    "gm"
);
```

### Python Integration
```python
import requests

def ask_agent(user_prompt, user_id, invoice_id, role):
    url = "http://localhost:8000/api/agent/ask"
    payload = {
        "user_prompt": user_prompt,
        "user_id": user_id,
        "invoice_id": invoice_id,
        "role": role
    }
    
    response = requests.post(url, json=payload)
    return response.json()

# Example usage
result = ask_agent(
    "What should I do about this invoice?",
    "user_123",
    "INV-73318",
    "gm"
)

print(f"Agent response: {result['markdown']}")
print(f"Confidence: {result['confidence']}%")
```

## 🚀 **Usage Scenarios**

### Scenario 1: Invoice Review
1. User opens an invoice
2. User types: "Why is this more expensive than usual?"
3. Frontend sends to `/api/agent/ask`
4. Agent responds with analysis and suggestions
5. Frontend displays response and suggested actions

### Scenario 2: Credit Request
1. User flags an item on an invoice
2. User asks: "Can I get a credit for this?"
3. Frontend sends to `/api/agent/suggest-credit`
4. Agent calculates credit amount and provides reasoning
5. Frontend shows credit suggestion with action buttons

### Scenario 3: Email Generation
1. User wants to contact supplier about an issue
2. User clicks "Generate Email" button
3. Frontend sends to `/api/agent/generate-email`
4. Agent creates professional email draft
5. Frontend displays email for user to review and send

## 🔒 **Error Handling**

All endpoints return consistent error responses:
```json
{
    "error": "Error message",
    "markdown": "⚠️ The agent encountered an error. Please try again.",
    "actions": [],
    "confidence": 0,
    "entities": {},
    "urgency": "low"
}
```

## 📈 **Performance**

- **Response Time:** Typically 1-3 seconds for agent responses
- **Fallback:** Automatic fallback responses when AI models are unavailable
- **Caching:** Client-side caching recommended for repeated questions
- **Rate Limiting:** Consider implementing rate limiting for production use

## 🎯 **Next Steps**

1. **Frontend Integration:** Connect the API endpoints to the React frontend
2. **Authentication:** Add user authentication and authorization
3. **Rate Limiting:** Implement rate limiting for production
4. **Monitoring:** Add metrics and monitoring for agent performance
5. **Caching:** Implement response caching for common questions

## ✅ **Implementation Status**

- ✅ Agent API endpoints created
- ✅ Integrated into main FastAPI app
- ✅ Comprehensive error handling
- ✅ Health check and capabilities endpoints
- ✅ Convenience endpoints for common tasks
- ✅ Role-aware responses
- ✅ Conversation memory support
- ✅ Testing framework implemented
- ✅ Documentation completed

The agent API is now **fully functional** and ready for frontend integration! 