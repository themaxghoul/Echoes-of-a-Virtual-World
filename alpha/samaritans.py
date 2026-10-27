"""Transparent offline dialogue, grounded in character goals and remembered turns.

These are autonomous game characters with contextual rules, not a claim of general
intelligence. The optional language-model adapter only produces dialogue, never actions.
"""

SAMARITANS = [
    {
        "id": "mira",
        "name": "Mira",
        "role": "ecologist",
        "home": [4, 4],
        "goal": "compare soil moisture in forest and meadow",
        "activities": [
            "cataloguing soil samples",
            "checking the woodland",
            "writing field notes",
        ],
    },
    {
        "id": "oren",
        "name": "Oren",
        "role": "builder",
        "home": [-5, 3],
        "goal": "establish a settlement with shelter and a shared research lab",
        "activities": [
            "surveying shelter sites",
            "measuring stone",
            "planning a shared lab",
        ],
    },
    {
        "id": "sol",
        "name": "Sol",
        "role": "mediator",
        "home": [2, -5],
        "goal": "help settlers negotiate peaceful knowledge-sharing agreements",
        "activities": [
            "listening to settlers",
            "recording agreements",
            "visiting the commons",
        ],
    },
]


def respond(npc, player, text, history):
    words = text.lower()
    prefix = f'{player["name"]}, '
    if any(term in words for term in ["help you", "need", "your goal", "working on"]):
        return (
            prefix
            + f'my goal is to {npc["goal"]}. I am {npc["activity"]}. '
            + {
                "mira": "You can help by sampling soil in a meadow and then a forest. Use Research at each site and tell me what changed.",
                "oren": f'You have {player["wood"]} wood and {player["stone"]} stone. A camp costs 8 wood and 2 stone. Find clear ground and build beside your position.',
                "sol": "Ask your neighbors what they need. Use Propose cooperation when you intend to record an agreement; ordinary conversation alone does not sign one.",
            }[npc["id"]]
        )
    if any(term in words for term in ["help", "how do", "where", "stuck"]):
        return (
            prefix
            + f'I can offer guidance while I {npc["goal"]}. Walk with WASD or the direction buttons. Forests provide wood, rocky ground provides stone, and meadows provide food. Gather, then build a camp; Research uses one food. What are you trying to build?'
        )
    if any(term in words for term in ["how are", "hello", "hi ", "friend", "feeling"]):
        return (
            prefix
            + f'I am curious about what we can learn together. I have been {npc["activity"]}. '
            + (
                "I remember our earlier conversation. "
                if history
                else "It is good to meet you. "
            )
            + "What brought you to this world?"
        )
    if any(
        term in words for term in ["peace", "trade", "diplom", "cooperat", "alliance"]
    ):
        return (
            prefix
            + "I favor peaceful knowledge sharing, provided everyone keeps their own choices. Use Propose cooperation to record those limited terms. This conversation does not transfer property, currency, or control."
        )
    if any(term in words for term in ["remember", "earlier", "last time"]):
        return prefix + (
            f'last time you told me: “{history[0]["text"][:180]}”. My current goal is still to {npc["goal"]}.'
            if history
            else "this is our first recorded conversation. Tell me what you would like us to work on."
        )
    if any(
        term in words
        for term in ["soil", "forest", "science", "experiment", "moisture"]
    ):
        return (
            prefix
            + f'you have recorded {player["research"]} field samples. Compare the same quantity across different terrain and keep other conditions fixed. Our moisture values are a simplified simulation; they are a hypothesis to test, not real measurements. What did your comparison show?'
        )
    return (
        prefix
        + f'you said “{text[:180]}”. From my work as a {npc["role"]}, I would connect that to my aim to {npc["goal"]}. '
        + ("We have spoken before, and I am keeping that context. " if history else "")
        + "Are you asking for practical help, proposing cooperation, or sharing how you feel? Tell me which, so we can take a useful next step."
    )
