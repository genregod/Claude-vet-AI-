import os
from anthropic import Anthropic
from typing import Optional

class ClaudeService:
    def __init__(self):
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        self._client = None
    
    @property
    def client(self):
        """Lazy initialization of Anthropic client"""
        if self._client is None and self.api_key:
            self._client = Anthropic(api_key=self.api_key)
        return self._client
    
    async def get_claim_assistance(self, veteran_info: dict, claim_details: dict) -> str:
        """
        Get AI assistance for VA disability claims
        """
        # Check if API key exists first before checking client
        if not self.api_key:
            return """⚠️ ANTHROPIC_API_KEY is not configured. 

To enable AI claim assistance:
1. Get an API key from https://www.anthropic.com/
2. Add it to backend/.env: ANTHROPIC_API_KEY=your_key_here
3. Restart the backend server

This is a demo response showing what the AI would provide:

CLAIM ASSESSMENT:
Your claim shows potential for approval with proper documentation. The conditions you've listed are commonly service-connected.

REQUIRED EVIDENCE:
1. Current medical diagnosis from a VA or private physician
2. Service treatment records showing in-service occurrence
3. Nexus letter linking current condition to service
4. Buddy statements from fellow service members (if applicable)

NEXT STEPS:
1. Gather all medical records
2. Schedule C&P examination when requested
3. Submit VA Form 21-526EZ
4. Consider working with a VSO

TIMELINE:
Initial claims typically take 90-120 days. Appeals may take 6-12 months.

Remember: Always consult with an accredited VSO or attorney for official representation."""
        
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
