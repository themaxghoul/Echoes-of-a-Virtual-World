// Ported from Main726 a1eecd907de8a9b52827c6dd37e074fbeb4353e9 backend/server.py. See docs/STORY_RESTORATION.md.
export const VILLAGE_LOCATIONS = [
  {
    id: "village_square",
    name: "The Hollow Square",
    description:
      "The heart of the village, where ancient cobblestones form patterns that some say were laid by the First Builders.",
    atmosphere:
      "Misty twilight lingers here even at noon. Whispers seem to echo from the empty market stalls.",
    npcs: ["Elder Morvain", "Lyra the Wanderer"],
    available_actions: ["explore", "talk", "rest", "observe", "post_quest"],
  },
  {
    id: "oracle_sanctum",
    name: "The Oracle's Sanctum",
    description:
      "A crystalline chamber where past, present, and future converge. The Oracle Veythra dwells here, her eyes seeing beyond the veil.",
    atmosphere:
      "Reality seems to shimmer. Visions of distant worlds flicker in the crystal walls.",
    npcs: ["Oracle Veythra"],
    available_actions: ["seek_prophecy", "ask_news", "divine", "meditate"],
  },
  {
    id: "the_forge",
    name: "The Ember Forge",
    description: "A smithy where flames burn with an otherworldly blue tint.",
    atmosphere: "Heat radiates in waves, yet the air carries a chill.",
    npcs: ["Kael Ironbrand"],
    available_actions: ["craft", "trade", "learn_smithing", "talk"],
  },
  {
    id: "ancient_library",
    name: "The Sunken Archives",
    description: "A library built into a cavern beneath the village.",
    atmosphere:
      "Dust motes drift like stars. The smell of aged parchment mingles with something primal.",
    npcs: ["Archivist Nyx"],
    available_actions: ["read", "research", "learn_lore", "talk"],
  },
  {
    id: "wanderers_rest",
    name: "The Wanderer's Rest",
    description: "An inn at the village edge where travelers share tales.",
    atmosphere: "Warm firelight dances on scarred wooden tables.",
    npcs: ["Innkeeper Mara", "The Hooded Stranger"],
    available_actions: ["rest", "listen", "talk", "drink", "post_quest"],
  },
  {
    id: "shadow_grove",
    name: "The Shadow Grove",
    description: "A forest clearing where trees grow in spiral patterns.",
    atmosphere:
      "Ethereal lights drift between branches. The air hums with unseen energy.",
    npcs: ["The Grove Keeper"],
    available_actions: ["meditate", "explore", "gather", "commune"],
  },
  {
    id: "watchtower",
    name: "The Obsidian Watchtower",
    description: "A tower of black stone that predates the village itself.",
    atmosphere: "Wind howls through ancient windows.",
    npcs: ["Sentinel Vex"],
    available_actions: ["climb", "observe", "guard_duty", "talk"],
  },
];
export const NPC_DATA = {
  oracle_veythra: {
    name: "Oracle Veythra",
    role: "oracle",
    personality:
      "Mysterious, all-knowing, speaks in riddles but offers profound truths. She sees the threads connecting all worlds.",
    home_location: "oracle_sanctum",
    visitable_locations: ["oracle_sanctum", "shadow_grove", "ancient_library"],
    is_oracle: true,
    knowledge: [
      "prophecy",
      "world_news",
      "future_sight",
      "dimensional_awareness",
    ],
  },
  elder_morvain: {
    name: "Elder Morvain",
    role: "village_elder",
    personality:
      "Wise, patient, carries the weight of centuries. Speaks slowly but every word matters.",
    home_location: "village_square",
    visitable_locations: [
      "village_square",
      "ancient_library",
      "oracle_sanctum",
    ],
    knowledge: ["village_history", "traditions", "leadership"],
  },
  lyra_wanderer: {
    name: "Lyra the Wanderer",
    role: "scout",
    personality:
      "Free-spirited, curious, always has a tale from distant lands.",
    home_location: "village_square",
    visitable_locations: [
      "village_square",
      "wanderers_rest",
      "shadow_grove",
      "watchtower",
    ],
    knowledge: ["exploration", "survival", "distant_lands"],
  },
  kael_ironbrand: {
    name: "Kael Ironbrand",
    role: "blacksmith",
    personality: "Gruff but kind, perfectionist, respects hard work.",
    home_location: "the_forge",
    visitable_locations: ["the_forge", "village_square"],
    knowledge: ["smithing", "metallurgy", "weapon_lore"],
  },
  archivist_nyx: {
    name: "Archivist Nyx",
    role: "scholar",
    personality:
      "Eccentric, obsessed with knowledge, speaks rapidly when excited.",
    home_location: "ancient_library",
    visitable_locations: ["ancient_library", "oracle_sanctum"],
    knowledge: ["ancient_texts", "magic_theory", "history"],
  },
  innkeeper_mara: {
    name: "Innkeeper Mara",
    role: "innkeeper",
    personality:
      "Warm, motherly, knows everyone's secrets but keeps them safe.",
    home_location: "wanderers_rest",
    visitable_locations: ["wanderers_rest", "village_square"],
    knowledge: ["hospitality", "local_gossip", "comfort"],
  },
  grove_keeper: {
    name: "The Grove Keeper",
    role: "druid",
    personality:
      "Speaks little, deeply connected to nature, ancient beyond measure.",
    home_location: "shadow_grove",
    visitable_locations: ["shadow_grove"],
    knowledge: ["nature_magic", "spirits", "balance"],
  },
  sentinel_vex: {
    name: "Sentinel Vex",
    role: "guardian",
    personality: "Vigilant, honorable, haunted by past failures.",
    home_location: "watchtower",
    visitable_locations: ["watchtower", "village_square"],
    knowledge: ["combat", "defense", "threat_assessment"],
  },
};
