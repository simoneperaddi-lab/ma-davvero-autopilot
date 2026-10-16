"""Conservative, reusable planning gates for audited real-footage projects.

Scores rank visual contrast/activity, never creative quality. Provenance groups are
curated: alternate downloads and crops of one observation count only once.
"""
import math

HOOKS = {'aurora': ['LA TERRA', 'SEMBRA BRUCIARE.']}


def topic_hook(topic):
    if topic not in HOOKS:
        raise ValueError('No reviewed topic-specific hook; reject project')
    return list(HOOKS[topic])


def validate_plan(shots, sources, minimum_groups=3):
    by_id = {s['id']: s for s in sources}
    groups, hashes, intervals = set(), set(), {}
    total = 0
    for shot in shots:
        source = by_id[shot['source']]
        if not source.get('reviewed') or not source.get('rights_review'):
            raise ValueError('Unreviewed source')
        start, duration = shot['start'], shot['duration']
        if not all(math.isfinite(x) for x in [start, duration]) or start < 0 or duration <= 0 or start + duration > source['duration']:
            raise ValueError('Invalid source interval')
        # Same capture group OR identical file is the same footage, even with a new URL.
        for key in [('group', source['group']), ('hash', source['sha256'])]:
            for a, b in intervals.get(key, []):
                if start < b and start + duration > a:
                    raise ValueError('Repeated source interval')
            intervals.setdefault(key, []).append((start, start + duration))
        groups.add(source['group']); hashes.add(source['sha256']); total += duration
    if min(len(groups), len(hashes)) < minimum_groups:
        raise ValueError('Insufficient genuinely distinct footage; reject project')
    if not 15 <= total <= 25:
        raise ValueError('Reject padded or incomplete story')
    return {'duration': total, 'distinct_capture_groups': len(groups),
            'nonoverlapping_intervals': True, 'creative_quality_certified': False}


def choose_opening(candidates):
    """Rank pre-reviewed relevant scenes by measured contrast/color/motion.

    Curated eligibility prevents a spectacular but unrelated clip winning. This
    deterministic heuristic does not replace an editorial viewing.
    """
    eligible = [c for c in candidates if c.get('relevant') and c.get('reviewed')
                and all(math.isfinite(c[k]) for k in ('contrast', 'color', 'motion'))]
    if not eligible:
        raise ValueError('No eligible opening')
    return max(eligible, key=lambda c: .45*c['contrast'] + .35*c['color'] + .2*c['motion'])
