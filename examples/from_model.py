"""Use after any model response. This example itself makes no model calls."""
from verbatim_guard import check_bundle

source = 'The trial included 48 participants.'
# In your app, parse this structure from the model's structured output.
model_output = [{'id': 'sample-size', 'source': 'study',
                 'quote': 'The trial included 480 participants.'}]
report = check_bundle({'sources': {'study': source}, 'claims': model_output})
if not report['ok']:
    print('Hold the answer for review:', report['results'][0]['status'])
else:
    print('Quotation matched. Semantic support still needs separate review.')
