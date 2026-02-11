import os
from anthropic import Anthropic
from typing import Optional

class ClaudeService:
    def __init__(self):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is not set")
        self.client = Anthropic(api_key=api_key)
    
    async def get_claim_assistance(self, veteran_info: dict, claim_details: dict) -> str:
        """
        Get AI assistance for VA disability claims
        """
        claim_type = claim_details.get('claim_type', 'initial')
        
        prompt = f"""You are an expert VA disability claims assistant helping veterans navigate the VA claims process. A veteran needs assistance with their claim:

Veteran Information:
- Name: {veteran_info.get('name', 'Unknown')}
- Service Branch: {veteran_info.get('service_branch', 'Unknown')}
- Service Dates: {veteran_info.get('service_dates', 'Not provided')}
- Discharge Status: {veteran_info.get('discharge_status', 'Not provided')}

Claim Type: {claim_type.upper()}
Claimed Conditions/Disabilities:
{claim_details.get('conditions', 'Not specified')}

Service Connection Explanation:
{claim_details.get('service_connection', 'Not provided')}

Evidence Available:
{claim_details.get('evidence_description', 'Not provided')}

Please provide:
1. An assessment of the claim's strength and key considerations
2. Required evidence and documentation needed (medical records, buddy statements, service records, etc.)
3. Specific steps to take next in the claims process
4. Common pitfalls to avoid
5. Timeline expectations for this type of claim
6. If this is an appeal, specific strategies for strengthening the case

Important: This is for informational and educational purposes only. Always consult with an accredited VSO (Veterans Service Officer) or attorney for official representation."""

        try:
            message = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=2048,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            return message.content[0].text
        except Exception as e:
            return f"Error getting AI assistance: {str(e)}"

claude_service = ClaudeService()
