"""
lifestyle_data.py
=================
Parkinson's Health, Nutrition & Lifestyle Educational Guidance Data.
Curated practical guidance focused on familiar Indian foods, dietary habits,
medication & protein timing, exercise, sleep, and fall prevention.

Educational prototype — Not a medical prescription.
"""

from typing import Dict, Any, List

LIFESTYLE_DISCLAIMER = (
    "Educational Health & Lifestyle Notice: This content provides general nutritional, "
    "exercise, and lifestyle education for individuals living with Parkinson's disease. "
    "Dietary needs and medication schedules vary with age, clinical stage, comorbidities, "
    "and medications. Food does not cure Parkinson's disease or stop its progression. "
    "Always consult your neurologist and registered clinical dietitian before making "
    "significant changes to your diet, supplements, exercise, or medication schedule."
)

INDIAN_FOOD_CATEGORIES = [
    {
        "category": "Vegetables & Leafy Greens",
        "benefits": "Rich in antioxidants, polyphenols, magnesium, and dietary fiber supporting digestive motility.",
        "examples": [
            "Palak (spinach) and methi (fenugreek leaves) cooked with mild spices",
            "Drumstick (moringa) in sambar or dal",
            "Ridge gourd (turai) and bottle gourd (lauki) — gentle on digestion",
            "Carrots, beetroot, and pumpkin — rich in beta-carotene and dietary fiber",
            "Bitter gourd (karela) and beans cooked soft for easier chewing",
        ],
    },
    {
        "category": "Fruits",
        "benefits": "Natural hydration, dietary fiber for constipation relief, and essential vitamins.",
        "examples": [
            "Ripe papaya (soft, rich in digestive enzymes and fiber)",
            "Guava (rich in vitamin C and insoluble fiber — seeds removed if swallowing is difficult)",
            "Pomegranate arils or fresh strained juice",
            "Ripe bananas (gentle potassium source and easy to chew)",
            "Oranges, sweet lime (mosambi), and amla (Indian gooseberry)",
        ],
    },
    {
        "category": "Whole Grains & Millets",
        "benefits": "Complex carbohydrates providing sustained energy and supporting gut microbiome balance.",
        "examples": [
            "Ragi (finger millet) — as ragi mudde, porridge (kanji), or soft ragi dosa",
            "Jowar (sorghum) or Bajra (pearl millet) rotis served soft with ghee",
            "Hand-pounded or brown rice, boiled parboiled rice with dal",
            "Whole-wheat soft phulkas / chapatis",
            "Rolled oats cooked with vegetable broth or mild milk",
        ],
    },
    {
        "category": "Pulses, Beans & Legumes",
        "benefits": "Plant-based protein, iron, and potassium. Note protein-medication timing advice.",
        "examples": [
            "Yellow moong dal — easiest to digest, gentle on sensitive stomachs",
            "Toor dal and chana dal in traditional sambar and rasam",
            "Steamed sundal (boiled white/black chickpeas or green gram tempered with curry leaves and mustard)",
            "Well-cooked rajma (kidney beans) and black urad dal in moderation",
        ],
    },
    {
        "category": "Nuts, Seeds & Healthy Fats",
        "benefits": "Omega-3 fatty acids, vitamin E, and healthy calories to prevent unintentional weight loss.",
        "examples": [
            "Almonds (soaked overnight and peeled for easier chewing and digestion)",
            "Walnuts (excellent plant source of ALA omega-3 fatty acids)",
            "Roasted flaxseed powder mixed into curd or dough",
            "Chia seeds soaked in water or coconut water",
            "Pure cow's ghee in moderate amounts for lubrication and calorie support",
        ],
    },
    {
        "category": "Dairy & Protein Alternatives",
        "benefits": "Calcium for bone density (crucial for fall risk) and gut-friendly probiotics.",
        "examples": [
            "Fresh homemade curd (dahi) or spiced buttermilk (chaas / mor)",
            "Soft paneer (cottage cheese) in small to moderate portions",
            "Eggs (soft boiled, poached, or scrambled) according to dietary preference",
            "Steamed or lightly curried freshwater fish (rohu, katla, sardines)",
            "Firm or soft tofu for plant-based diets",
        ],
    },
]

MEDICATION_PROTEIN_TIMING = {
    "title": "Medication & Protein Timing (Levodopa Interaction)",
    "summary": (
        "Dietary protein contains large neutral amino acids (LNAAs) that utilize the same "
        "active transport mechanism across the intestinal wall and blood-brain barrier as Levodopa."
    ),
    "rules": [
        "Do NOT eliminate protein: Muscle mass, immune function, and wound healing require adequate daily protein.",
        "Do NOT start a low-protein diet on your own: Severe protein restriction can cause malnutrition and muscle weakness.",
        "Coordinate meal timing: Many neurologists suggest taking Levodopa 30 to 60 minutes BEFORE meals, or 1 to 2 hours AFTER meals, accompanied by water.",
        "Evening protein distribution: Some patients with motor fluctuations find benefit in consuming larger protein portions during the evening dinner when motor demands are lower, as approved by their physician.",
        "Individual variation: Not everyone experiences food-medication interactions. Discuss with your neurologist and dietitian before changing routines.",
        "Never alter doses: Never modify medication dosages, frequencies, or formulations without doctor approval.",
    ],
}

EXERCISE_GUIDANCE = [
    {
        "activity": "Walking & Cadence Cues",
        "details": "Regular walking on even surfaces with sturdy, non-slip footwear. Using rhythmic cues (music, counting strides 1-2-1-2, or a metronome) helps overcome gait freezing.",
    },
    {
        "activity": "Clinician-Approved Stretching",
        "details": "Daily gentle stretching of chest/pecs, hamstrings, calves, and spinal rotation helps combat Parkinsonian stooped posture and muscle rigidity.",
    },
    {
        "activity": "Supervised Balance Exercises",
        "details": "Tandem standing (one foot in front of the other), single-leg balance near a sturdy rail, and Tai Chi movements improve postural stability. Always supervised if fall history exists.",
    },
    {
        "activity": "Strength & Resistance Training",
        "details": "Light resistance bands, sit-to-stand repetitions from a sturdy chair, and bodyweight exercises preserve leg strength and ease transfer movements.",
    },
    {
        "activity": "Speech & Swallowing Support",
        "details": "Lee Silverman Voice Treatment (LSVT LOUD) principles, vocal projection exercises, maintaining upright posture during meals, and chin-tuck swallowing techniques when indicated.",
    },
    {
        "activity": "Sleep Hygiene & Fall Prevention",
        "details": "Consistent sleep schedule, avoiding screens before bed, removing loose rugs, installing night lights in hallways to the bathroom, and avoiding rushing when getting up.",
    },
]

SAMPLE_INDIAN_MEAL_PLANS = {
    "vegetarian": [
        {"meal": "Early Morning (6:30 AM)", "item": "Warm water with a pinch of cumin (jeera) or 1 glass of plain lukewarm water. (Medication window if prescribed)"},
        {"meal": "Breakfast (8:00 AM)", "item": "3 soft steamed idlis with mild vegetable sambar and coriander-mint chutney, OR 1 bowl of vegetable oats porridge with grated carrot."},
        {"meal": "Mid-Morning (10:30 AM)", "item": "1 cup of fresh ripe papaya cubes OR guava slices + 4-5 soaked and peeled almonds."},
        {"meal": "Lunch (1:00 PM)", "item": "1-2 soft whole-wheat phulkas OR 1 cup steamed rice + 1 bowl yellow moong dal + 1 cup soft lauki (bottle gourd) sabzi + a small glass of thin buttermilk (chaas) with roasted cumin."},
        {"meal": "Evening Snack (4:30 PM)", "item": "1 small bowl of steamed chickpea sundal (boiled with curry leaves) OR roasted makhana (fox nuts) + warm herbal ginger-lemon tea."},
        {"meal": "Dinner (7:30 PM)", "item": "Vegetable moong dal khichdi with 1 teaspoon cow's ghee, served with a bowl of soft cooked mixed vegetables (beans, carrot, pumpkin)."},
        {"meal": "Bedtime (9:30 PM)", "item": "Warm water or light chamomile tea. Adequate hydration earlier in the day to minimize nocturnal awakenings."},
    ],
    "non_vegetarian": [
        {"meal": "Early Morning (6:30 AM)", "item": "Warm lukewarm water. (Levodopa timing as directed by neurologist)"},
        {"meal": "Breakfast (8:00 AM)", "item": "2 vegetable dosas with mint chutney and sambar, OR 2 scrambled eggs (soft texture) with whole-grain toast."},
        {"meal": "Mid-Morning (10:30 AM)", "item": "1 ripe banana OR a bowl of fresh pomegranate arils + 4 soaked walnuts."},
        {"meal": "Lunch (1:00 PM)", "item": "1 cup steamed rice or 2 soft phulkas + 1 cup mixed vegetable dal + soft steamed vegetable sabzi + a glass of thin buttermilk."},
        {"meal": "Evening Snack (4:30 PM)", "item": "Boiled chana sundal OR warm vegetable soup + green tea."},
        {"meal": "Dinner (7:30 PM)", "item": "1-2 soft chapatis + 1 portion of gently curried or steamed fish (e.g. rohu, katla, or salmon) OR soft stewed chicken with vegetables. (Concentrating animal protein at dinner if recommended for daytime levodopa absorption)."},
        {"meal": "Bedtime (9:30 PM)", "item": "Warm water. Ensure fluid intake was completed earlier in the evening."},
    ],
    "south_indian": [
        {"meal": "Early Morning (6:30 AM)", "item": "Warm water with jeera or plain lukewarm water."},
        {"meal": "Breakfast (8:00 AM)", "item": "2-3 soft idlis with vegetable sambar and tomato chutney, OR ragi semiya upma cooked with peas and carrots."},
        {"meal": "Mid-Morning (10:30 AM)", "item": "Fresh ripe papaya or pomegranate + 5 soaked almonds."},
        {"meal": "Lunch (1:00 PM)", "item": "1 cup boiled red or parboiled rice + toor dal sambar with drumstick and pumpkin + cabbage poriyal + small cup of fresh rasam."},
        {"meal": "Evening Snack (4:30 PM)", "item": "Boiled sundal (white or black chickpeas tempered with mustard and curry leaves) + warm mild filter coffee or herbal tea."},
        {"meal": "Dinner (7:30 PM)", "item": "2 soft ragi dosas OR 2 whole-wheat chapatis with vegetable kurma or dal kootu."},
        {"meal": "Bedtime (9:30 PM)", "item": "Warm water or spiced cumin water."},
    ],
    "north_indian": [
        {"meal": "Early Morning (6:30 AM)", "item": "Lukewarm water with lemon or plain warm water."},
        {"meal": "Breakfast (8:00 AM)", "item": "1 soft methi or paneer paratha (light oil/ghee) with homemade curd, OR vegetable poha with roasted peanuts."},
        {"meal": "Mid-Morning (10:30 AM)", "item": "1 seasonal fruit (apple, papaya, or pear) + soaked walnuts."},
        {"meal": "Lunch (1:00 PM)", "item": "2 soft phulkas + 1 bowl yellow dal tadka + soft bhindi (okra) or lauki sabzi + small katori of cucumber raita."},
        {"meal": "Evening Snack (4:30 PM)", "item": "Roasted makhana OR boiled moong sprout chaat (steamed soft) + warm ginger tea."},
        {"meal": "Dinner (7:30 PM)", "item": "Light vegetable khichdi OR 2 soft rotis with palak dal or bottle gourd kofta curry."},
        {"meal": "Bedtime (9:30 PM)", "item": "Warm water or turmeric milk (haldi doodh) in moderation."},
    ]
}

SPECIALIZED_CONCERN_TIPS = {
    "constipation": [
        "Ensure 6-8 glasses of fluid daily, starting with warm water upon waking.",
        "Increase soluble fiber with stewed prunes, ripe papaya, soaked chia seeds, and cooked oats.",
        "Include fermented foods such as fresh curd (dahi) or traditional buttermilk for gut probiotics.",
        "Take a brisk 15-20 minute walk daily (if safely able) to stimulate bowel motility.",
    ],
    "medication_timing": [
        "Discuss protein distribution with your neurologist — having high protein at night can keep daytime levodopa absorption consistent.",
        "Take levodopa with full glass of water, usually 30-60 minutes before food unless nausea occurs.",
        "If nausea occurs, discuss taking medication with a low-protein carbohydrate snack (like a plain cracker, toast, or banana).",
        "Avoid iron supplements within 2 hours of taking levodopa, as iron binds levodopa in the gut.",
    ],
    "swallowing": [
        "Sit completely upright (90 degrees) during meals and remain upright for 30 minutes after eating.",
        "Choose soft, moist foods with uniform texture (khichdi, pureed dals, soft idli soaked in sambar).",
        "Avoid mixed-consistency foods (e.g. soup with large tough chunks) if coughing or throat clearing occurs.",
        "Work with a certified Speech-Language Pathologist for personalized swallowing assessment.",
    ],
    "fatigue": [
        "Eat smaller, more frequent meals rather than heavy lunches that cause postprandial fatigue.",
        "Include complex whole grains (oats, ragi, brown rice) for steady glucose delivery.",
        "Stay hydrated throughout the day; mild dehydration significantly exacerbates Parkinsonian fatigue.",
        "Practice regular sleep hygiene: consistent bedtimes and exposure to natural morning daylight.",
    ]
}


def get_personalized_lifestyle_guide(
    dietary_pref: str = "vegetarian",
    cuisine_pref: str = "all",
    primary_concern: str = "general",
) -> Dict[str, Any]:
    """
    Return customized educational nutrition, exercise, and meal guidance
    based on user's dietary and symptom focus.
    """
    pref_key = dietary_pref.lower()
    if pref_key not in SAMPLE_INDIAN_MEAL_PLANS:
        if "non" in pref_key:
            pref_key = "non_vegetarian"
        elif "south" in cuisine_pref.lower():
            pref_key = "south_indian"
        elif "north" in cuisine_pref.lower():
            pref_key = "north_indian"
        else:
            pref_key = "vegetarian"

    meal_plan = SAMPLE_INDIAN_MEAL_PLANS.get(pref_key, SAMPLE_INDIAN_MEAL_PLANS["vegetarian"])

    concern_key = primary_concern.lower()
    if concern_key in SPECIALIZED_CONCERN_TIPS:
        concern_tips = SPECIALIZED_CONCERN_TIPS[concern_key]
    else:
        concern_tips = [
            "Maintain a diverse, colorful diet rich in antioxidants from vegetables and fruits.",
            "Stay adequately hydrated with 6-8 glasses of water throughout the daytime.",
            "Coordinate medication timing with protein intake in consultation with your doctor.",
            "Incorporate safe daily walking and gentle stretching into your routine.",
        ]

    return {
        "dietary_preference": dietary_pref,
        "cuisine_preference": cuisine_pref,
        "primary_concern": primary_concern,
        "food_categories": INDIAN_FOOD_CATEGORIES,
        "medication_protein_timing": MEDICATION_PROTEIN_TIMING,
        "exercise_guidance": EXERCISE_GUIDANCE,
        "meal_plan": meal_plan,
        "concern_specific_tips": concern_tips,
        "disclaimer": LIFESTYLE_DISCLAIMER,
    }
