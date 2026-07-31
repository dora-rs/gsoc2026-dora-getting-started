def decide(context):
    latest = context['history'][-1]
    rates = context['rates']
    switches = context['switch_state']
    freshness = context['freshness_seconds']
    actions = []

    if switches['cooling']:
        if latest['temperature_c'] <= 35 and rates['temperature_c_per_s'] < 0:
            actions.append({'switch': 'cooling', 'enabled': False})
    elif latest['temperature_c'] >= 40 and rates['temperature_c_per_s'] >= 0:
        actions.append({'switch': 'cooling', 'enabled': True})

    if switches['relief']:
        if latest['pressure_kpa'] <= 165 and rates['pressure_kpa_per_s'] < 0:
            actions.append({'switch': 'relief', 'enabled': False})
    elif latest['pressure_kpa'] >= 170 and rates['pressure_kpa_per_s'] >= 0:
        actions.append({'switch': 'relief', 'enabled': True})

    observe = []
    if switches['cooling'] or latest['temperature_c'] >= 50 or freshness['temperature'] >= 12:
        observe.append('temperature_rgb')
    if switches['relief'] or latest['pressure_kpa'] >= 180 or freshness['pressure'] >= 12:
        observe.append('pressure')
    if not observe:
        observe = ['pressure', 'temperature_rgb']

    if actions:
        observe_after_seconds = 3
    elif switches['cooling'] or switches['relief']:
        observe_after_seconds = 4
    elif latest['temperature_c'] >= 50 or latest['pressure_kpa'] >= 180:
        observe_after_seconds = 5
    else:
        observe_after_seconds = 10

    return {
        'observe': observe,
        'actions': actions,
        'observe_after_seconds': observe_after_seconds,
        'reason': 'adaptive control from values, trends, freshness, and state',
    }