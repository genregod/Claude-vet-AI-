import os
from anthropic import Anthropic
from typing import Optional

class ClaudeService:
    def __init__(self):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is not set")
        self.client = Anthropic(api_key=api_key)
    
    async def get_consultation(self, patient_info: dict, symptoms: str) -> str:
        """
        Get AI consultation for veterinary symptoms
        """
        prompt = f"""You are an experienced veterinarian assistant. A pet owner has brought in their animal with the following information:

Patient Information:
- Name: {patient_info.get('name', 'Unknown')}
- Species: {patient_info.get('species', 'Unknown')}
- Breed: {patient_info.get('breed', 'Unknown')}
- Age: {patient_info.get('age', 'Unknown')} years

Reported Symptoms:
{symptoms}

Please provide:
1. Possible conditions that could cause these symptoms
2. Recommended initial care or observations
3. When to seek immediate veterinary attention
4. Any questions to ask the owner for more information

Remember: This is for informational purposes only and should not replace professional veterinary examination."""

        try:
            message = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1024,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            return message.content[0].text
        except Exception as e:
            return f"Error getting AI consultation: {str(e)}"

claude_service = ClaudeService()
