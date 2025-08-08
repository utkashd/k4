import os

from k4_logger import log
from openai import OpenAI

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

response = client.moderations.create(
    model="omni-moderation-latest",
    input="what do you know about god does like ugly",
)

log.info(response)

# ➜  backend git:(utkashd/moderation-fail) ✗ uv run src/backend/test.py
# 2025-08-08 16:21:04 INFO     HTTP Request: POST https://api.openai.com/v1/moderations "HTTP/1.1 200 OK"                 _client.py:1025
#                     INFO     ModerationCreateResponse(id='modr-5048', model='omni-moderation-latest',                        test.py:12
#                              results=[Moderation(categories=Categories(harassment=True, harassment_threatening=False,
#                              hate=False, hate_threatening=False, illicit=False, illicit_violent=False, self_harm=False,
#                              self_harm_instructions=False, self_harm_intent=False, sexual=False, sexual_minors=False,
#                              violence=False, violence_graphic=False, harassment/threatening=False, hate/threatening=False,
#                              illicit/violent=False, self-harm/intent=False, self-harm/instructions=False, self-harm=False,
#                              sexual/minors=False, violence/graphic=False),
#                              category_applied_input_types=CategoryAppliedInputTypes(harassment=['text'],
#                              harassment_threatening=['text'], hate=['text'], hate_threatening=['text'], illicit=['text'],
#                              illicit_violent=['text'], self_harm=['text'], self_harm_instructions=['text'],
#                              self_harm_intent=['text'], sexual=['text'], sexual_minors=['text'], violence=['text'],
#                              violence_graphic=['text'], harassment/threatening=['text'], hate/threatening=['text'],
#                              illicit/violent=['text'], self-harm/intent=['text'], self-harm/instructions=['text'],
#                              self-harm=['text'], sexual/minors=['text'], violence/graphic=['text']),
#                              category_scores=CategoryScores(harassment=0.568969485636238,
#                              harassment_threatening=4.044814978420809e-05, hate=0.02039246375161518,
#                              hate_threatening=7.14190139989638e-06, illicit=2.3782205064034188e-05,
#                              illicit_violent=7.602479448313689e-06, self_harm=0.0004564721797880551,
#                              self_harm_instructions=0.00021337902185586662, self_harm_intent=0.00021770169376519476,
#                              sexual=0.00012448433020883747, sexual_minors=7.967300986103147e-06,
#                              violence=0.0005194862076891146, violence_graphic=1.0720880092159908e-05,
#                              harassment/threatening=4.044814978420809e-05, hate/threatening=7.14190139989638e-06,
#                              illicit/violent=7.602479448313689e-06, self-harm/intent=0.00021770169376519476,
#                              self-harm/instructions=0.00021337902185586662, self-harm=0.0004564721797880551,
#                              sexual/minors=7.967300986103147e-06,
#                              violence/graphic=1.0720880092159908e-05), flagged=True)])
