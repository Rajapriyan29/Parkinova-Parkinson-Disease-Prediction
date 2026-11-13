"""
patient_form.py
---------------
Patient Information & Cognitive Symptom Assessment form for Parkinova.
Features a multi-slide wizard interface with seamless slide navigation,
validation, stepper indicator, and "Go to Next Slide" buttons.

Collects:
  - Basic demographic information (age, patient code, gender)
  - 13 cognitive / behavioural symptom questions across 4 categories:
    (Cognitive, Emotional, Sleep & Energy, Functional)
  - Voluntary research consent confirmation
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

import customtkinter as ctk
from tkinter import messagebox

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Vintage Editorial Palette (Warm Cream, Deep Forest Green, Coral Red)
# ---------------------------------------------------------------------------
COLORS = {
    "bg": "#F5F0D8",               # Primary Background: Warm cream / vintage ivory
    "card": "#FFF9E9",             # Highlight Color: Warm off-white
    "navy": "#123F2D",             # Primary Text & Headings: Deep forest green
    "cyan": "#F0442E",             # Accent Color: Vibrant coral red
    "cyan_hover": "#D43823",       # Slightly darker coral
    "cyan_light": "#EAE5CC",       # Subtle Background: Pale beige
    "text": "#123F2D",             # Deep forest green
    "muted": "#365747",            # Secondary Text: Muted dark green
    "red": "#F0442E",              # Coral red
    "green": "#123F2D",            # Deep forest green
    "green_light": "#EAE5CC",      # Pale beige
    "border": "#B8C4A5",           # Border Color: Muted sage green
    "amber_bg": "#EAE5CC",         # Pale beige
    "amber_border": "#D77B65",     # Soft terracotta
    "row_alt": "#EAE5CC",          # Pale beige
}

# ---------------------------------------------------------------------------
# Response options
# ---------------------------------------------------------------------------
RESPONSE_OPTIONS = [
    "Never",
    "Rarely",
    "Sometimes",
    "Often",
    "Always",
    "Prefer not to answer",
]

RESPONSE_VALUES = {
    "Never": 0,
    "Rarely": 1,
    "Sometimes": 2,
    "Often": 3,
    "Always": 4,
    "Prefer not to answer": -1,
}

# ---------------------------------------------------------------------------
# Symptom questions
# ---------------------------------------------------------------------------
SYMPTOM_QUESTIONS = [
    {
        "id": "memory_difficulties",
        "label": "Memory Difficulties",
        "question": "How often do you experience difficulty remembering recent events, names, or where you placed things?",
        "category": "Cognitive",
    },
    {
        "id": "concentration",
        "label": "Difficulty Concentrating",
        "question": "How often do you find it hard to focus or maintain attention on a task?",
        "category": "Cognitive",
    },
    {
        "id": "decision_making",
        "label": "Problems with Decision-Making",
        "question": "How often do you struggle to make decisions, even simple everyday ones?",
        "category": "Cognitive",
    },
    {
        "id": "mood_changes",
        "label": "Changes in Mood",
        "question": "How often do you notice unexpected or unexplained changes in your mood?",
        "category": "Emotional",
    },
    {
        "id": "anxiety",
        "label": "Feelings of Anxiety",
        "question": "How often do you feel anxious, worried, or on edge without a clear reason?",
        "category": "Emotional",
    },
    {
        "id": "depression",
        "label": "Symptoms of Depression",
        "question": "How often do you feel persistently sad, hopeless, or lose interest in activities you used to enjoy?",
        "category": "Emotional",
    },
    {
        "id": "emotional_wellbeing",
        "label": "Self-Reported Emotional Well-being",
        "question": "Overall, how often do you feel that your emotional well-being has changed compared to how you usually feel?",
        "category": "Emotional",
    },
    {
        "id": "sleep_disturbances",
        "label": "Sleep Disturbances",
        "question": "How often do you experience difficulty falling asleep, staying asleep, or feel unrested after sleeping?",
        "category": "Sleep & Energy",
    },
    {
        "id": "mental_fatigue",
        "label": "Mental Fatigue",
        "question": "How often do you feel mentally exhausted or drained, even without significant physical activity?",
        "category": "Sleep & Energy",
    },
    {
        "id": "reduced_motivation",
        "label": "Reduced Motivation",
        "question": "How often do you feel a lack of motivation or drive to start or complete tasks?",
        "category": "Sleep & Energy",
    },
    {
        "id": "daily_activities",
        "label": "Difficulty with Daily Activities",
        "question": "How often do you find it harder than usual to perform routine daily tasks (e.g., cooking, managing finances)?",
        "category": "Functional",
    },
    {
        "id": "thinking_speed",
        "label": "Changes in Thinking Speed",
        "question": "How often do you notice that your thoughts feel slower or that it takes longer to process information?",
        "category": "Functional",
    },
    {
        "id": "planning_organizing",
        "label": "Difficulty Planning & Organizing",
        "question": "How often do you struggle to plan ahead, organize steps, or follow through with multi-step tasks?",
        "category": "Functional",
    },
]

CATEGORIES = ["Cognitive", "Emotional", "Sleep & Energy", "Functional"]

CATEGORY_COLORS = {
    "Cognitive":      "#123F2D",   # Deep forest green
    "Emotional":      "#D77B65",   # Soft terracotta
    "Sleep & Energy": "#7A8D6E",   # Olive / sage
    "Functional":     "#365747",   # Muted dark green
}

SLIDES_CONFIG = [
    {
        "id": "demographics",
        "title": "Patient Demographics & Identification",
        "short_title": "1. Demographics",
        "subtitle": "Record patient identification code, age, and research guidelines",
        "icon": "👤",
        "next_label": "Go to Next Slide: Cognitive  →",
    },
    {
        "id": "cognitive",
        "title": "Cognitive Symptom Assessment",
        "short_title": "2. Cognitive",
        "subtitle": "Evaluate memory retention, mental concentration, and decision-making",
        "icon": "🧠",
        "category": "Cognitive",
        "next_label": "Go to Next Slide: Emotional & Mood  →",
    },
    {
        "id": "emotional",
        "title": "Emotional & Psychological Well-Being",
        "short_title": "3. Emotional",
        "subtitle": "Screen for unexpected mood fluctuations, anxiety, and depressive symptoms",
        "icon": "💜",
        "category": "Emotional",
        "next_label": "Go to Next Slide: Sleep & Energy  →",
    },
    {
        "id": "sleep_energy",
        "title": "Sleep Architecture & Energy Levels",
        "short_title": "4. Sleep & Energy",
        "subtitle": "Document sleep disturbances, mental exhaustion, and motivation levels",
        "icon": "⚡",
        "category": "Sleep & Energy",
        "next_label": "Go to Next Slide: Functional & Consent  →",
    },
    {
        "id": "functional",
        "title": "Functional Living & Research Consent",
        "short_title": "5. Functional & Consent",
        "subtitle": "Daily activities, processing speed, multi-step planning, and research consent",
        "icon": "📋",
        "category": "Functional",
        "next_label": "Save & Continue to MRI Upload  →",
    },
]


# ===========================================================================
# Patient Assessment Multi-Slide Form
# ===========================================================================

class PatientFormFrame(ctk.CTkFrame):
    """
    Multi-slide patient information and symptom assessment wizard.
    Includes stepper indicator, per-slide scrollable frames, and
    prominent 'Go to Next Slide' and 'Previous Slide' navigation buttons.
    """

    def __init__(self, parent, app_controller):
        super().__init__(parent, fg_color=COLORS["bg"], corner_radius=0)
        self.app_controller = app_controller
        self._responses: Dict[str, ctk.StringVar] = {}
        self._age_var = ctk.StringVar()
        self._patient_code_var = ctk.StringVar()
        self._gender_var = ctk.StringVar(value="Prefer not to say")
        self._consent_var = ctk.BooleanVar(value=False)
        self._status_var = ctk.StringVar(value="")

        # Slide state
        self._current_slide_idx: int = 0
        self._slide_frames: List[ctk.CTkFrame] = []
        self._stepper_buttons: List[ctk.CTkButton] = []

        self.build_ui()

    # -----------------------------------------------------------------------
    # UI Layout Construction
    # -----------------------------------------------------------------------

    def build_ui(self):
        self.grid_rowconfigure(0, weight=0)   # Header & Title
        self.grid_rowconfigure(1, weight=0)   # Stepper Bar
        self.grid_rowconfigure(2, weight=1)   # Active Slide Container
        self.grid_columnconfigure(0, weight=1)

        self._build_header()
        self._build_stepper()
        self._build_slides()

        # Display initial slide
        self.show_slide(0)

    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color=COLORS["card"], corner_radius=0, height=72, border_width=1, border_color=COLORS["border"])
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        header.grid_columnconfigure(0, weight=1)
        header.grid_columnconfigure(1, weight=0)

        left = ctk.CTkFrame(header, fg_color="transparent")
        left.grid(row=0, column=0, padx=24, pady=12, sticky="w")

        ctk.CTkLabel(
            left,
            text="📋  Patient Information & Symptom Assessment",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color=COLORS["navy"],
        ).pack(anchor="w")

        ctk.CTkLabel(
            left,
            text="Clinical research screening wizard  ·  Step-by-step evaluation slides",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=COLORS["muted"],
        ).pack(anchor="w")

        # Slide counter badge on the right
        self._slide_counter_badge = ctk.CTkLabel(
            header,
            text="Slide 1 of 5 (20%)",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=COLORS["cyan"],
            fg_color=COLORS["cyan_light"],
            corner_radius=6,
            padx=14,
            pady=6,
        )
        self._slide_counter_badge.grid(row=0, column=1, padx=24, pady=16, sticky="e")

    def _build_stepper(self):
        """Build clickable horizontal slide step indicators."""
        stepper_frame = ctk.CTkFrame(self, fg_color=COLORS["bg"], height=48, corner_radius=0)
        stepper_frame.grid(row=1, column=0, sticky="ew", padx=24, pady=(10, 4))
        stepper_frame.grid_columnconfigure(tuple(range(len(SLIDES_CONFIG))), weight=1, uniform="stepper")

        self._stepper_buttons.clear()

        for idx, slide_cfg in enumerate(SLIDES_CONFIG):
            btn = ctk.CTkButton(
                stepper_frame,
                text=slide_cfg["short_title"],
                height=36,
                corner_radius=8,
                fg_color=COLORS["card"],
                text_color=COLORS["muted"],
                font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold" if idx == 0 else "normal"),
                border_width=1,
                border_color=COLORS["border"],
                hover_color=COLORS["cyan_light"],
                command=lambda i=idx: self.jump_to_slide(i),
            )
            btn.grid(row=0, column=idx, padx=4, sticky="ew")
            self._stepper_buttons.append(btn)

    def _build_slides(self):
        """Construct a single high-performance scrollable container with lightweight slide frames."""
        self._scroll = ctk.CTkScrollableFrame(
            self,
            fg_color=COLORS["bg"],
            corner_radius=0,
        )
        self._scroll.grid(row=2, column=0, sticky="nsew", padx=0, pady=0)
        self._scroll.grid_columnconfigure(0, weight=1)

        self._slide_frames.clear()

        # Slide 0: Demographics & Guidelines
        slide_0 = ctk.CTkFrame(self._scroll, fg_color="transparent")
        slide_0.grid_columnconfigure(0, weight=1)
        self._populate_slide_0(slide_0)
        self._slide_frames.append(slide_0)

        # Slide 1: Cognitive Assessment
        slide_1 = ctk.CTkFrame(self._scroll, fg_color="transparent")
        slide_1.grid_columnconfigure(0, weight=1)
        self._populate_category_slide(slide_1, 1, "Cognitive")
        self._slide_frames.append(slide_1)

        # Slide 2: Emotional Assessment
        slide_2 = ctk.CTkFrame(self._scroll, fg_color="transparent")
        slide_2.grid_columnconfigure(0, weight=1)
        self._populate_category_slide(slide_2, 2, "Emotional")
        self._slide_frames.append(slide_2)

        # Slide 3: Sleep & Energy Assessment
        slide_3 = ctk.CTkFrame(self._scroll, fg_color="transparent")
        slide_3.grid_columnconfigure(0, weight=1)
        self._populate_category_slide(slide_3, 3, "Sleep & Energy")
        self._slide_frames.append(slide_3)

        # Slide 4: Functional Assessment & Consent
        slide_4 = ctk.CTkFrame(self._scroll, fg_color="transparent")
        slide_4.grid_columnconfigure(0, weight=1)
        self._populate_slide_4(slide_4)
        self._slide_frames.append(slide_4)

    # -----------------------------------------------------------------------
    # Slide 0: Demographics & Instructions
    # -----------------------------------------------------------------------

    def _populate_slide_0(self, parent):
        row = 0

        # Slide Header Banner
        row = self._build_slide_banner(
            parent,
            row,
            icon="👤",
            title="Slide 1 of 5: Patient Demographics & Identification",
            subtitle="Enter patient information before beginning the symptom evaluation questions."
        )

        # Disclaimer Alert Card
        row = self._build_disclaimer(parent, row)

        # Demographics Input Card
        card = ctk.CTkFrame(parent, fg_color=COLORS["card"], corner_radius=12, border_width=1, border_color=COLORS["border"])
        card.grid(row=row, column=0, padx=24, pady=(0, 14), sticky="ew")
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card,
            text="Patient Identification",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color=COLORS["navy"],
            anchor="w",
        ).grid(row=0, column=0, padx=20, pady=(16, 12), sticky="w")

        fields = ctk.CTkFrame(card, fg_color="transparent")
        fields.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="ew")
        fields.grid_columnconfigure(0, weight=1)
        fields.grid_columnconfigure(1, weight=1)
        fields.grid_columnconfigure(2, weight=1)

        # Patient Code
        self._field_label(fields, "Patient / Study Code", 0, 0)
        ctk.CTkEntry(
            fields,
            textvariable=self._patient_code_var,
            placeholder_text="e.g. PT-104  (Optional)",
            height=40,
            corner_radius=8,
            border_color=COLORS["border"],
            font=ctk.CTkFont(family="Segoe UI", size=13),
        ).grid(row=1, column=0, padx=(0, 14), pady=(0, 6), sticky="ew")

        # Age
        self._field_label(fields, "Age (years) *", 0, 1)
        ctk.CTkEntry(
            fields,
            textvariable=self._age_var,
            placeholder_text="e.g. 64",
            height=40,
            corner_radius=8,
            border_color=COLORS["border"],
            font=ctk.CTkFont(family="Segoe UI", size=13),
        ).grid(row=1, column=1, padx=(0, 14), pady=(0, 6), sticky="ew")

        # Gender
        self._field_label(fields, "Gender", 0, 2)
        ctk.CTkOptionMenu(
            fields,
            variable=self._gender_var,
            values=["Male", "Female", "Non-binary", "Prefer not to say"],
            height=40,
            corner_radius=8,
            fg_color=COLORS["card"],
            button_color=COLORS["navy"],
            button_hover_color=COLORS["cyan"],
            dropdown_fg_color=COLORS["card"],
            text_color=COLORS["text"],
            font=ctk.CTkFont(family="Segoe UI", size=13),
        ).grid(row=1, column=2, pady=(0, 6), sticky="ew")

        row += 1

        # Instructions Card
        row = self._build_instructions(parent, row)

        # In-Slide Action Navigation Card
        self._build_slide_nav_card(
            parent,
            row,
            slide_idx=0,
            next_label="Go to Next Slide: Cognitive Assessment  →",
            helper_text="Next step: 3 questions on memory retention, focus, and decision making."
        )

    # -----------------------------------------------------------------------
    # Slides 1, 2, 3: Symptom Categories
    # -----------------------------------------------------------------------

    def _populate_category_slide(self, parent, slide_idx: int, category: str):
        row = 0
        cfg = SLIDES_CONFIG[slide_idx]

        # Slide Header Banner
        row = self._build_slide_banner(
            parent,
            row,
            icon=cfg["icon"],
            title=f"Slide {slide_idx + 1} of 5: {cfg['title']}",
            subtitle=cfg["subtitle"]
        )

        questions = [q for q in SYMPTOM_QUESTIONS if q["category"] == category]
        cat_color = CATEGORY_COLORS.get(category, COLORS["navy"])

        for q_idx, q in enumerate(questions):
            q_card = ctk.CTkFrame(
                parent,
                fg_color=COLORS["card"],
                corner_radius=10,
                border_width=1,
                border_color=COLORS["border"],
            )
            q_card.grid(row=row, column=0, padx=24, pady=(0, 10), sticky="ew")
            q_card.grid_columnconfigure(0, weight=1)

            # Category badge + question title
            header_row = ctk.CTkFrame(q_card, fg_color="transparent")
            header_row.grid(row=0, column=0, padx=20, pady=(14, 4), sticky="ew")
            header_row.grid_columnconfigure(1, weight=1)

            badge = ctk.CTkFrame(header_row, fg_color=cat_color, corner_radius=4, width=6, height=18)
            badge.grid(row=0, column=0, padx=(0, 8))
            badge.grid_propagate(False)

            ctk.CTkLabel(
                header_row,
                text=f"{q_idx + 1}.  {q['label']}",
                font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                text_color=COLORS["navy"],
                anchor="w",
            ).grid(row=0, column=1, sticky="w")

            # Question description
            ctk.CTkLabel(
                q_card,
                text=q["question"],
                font=ctk.CTkFont(family="Segoe UI", size=12),
                text_color=COLORS["text"],
                wraplength=860,
                justify="left",
                anchor="w",
            ).grid(row=1, column=0, padx=34, pady=(0, 12), sticky="w")

            # Radio responses
            self._responses[q["id"]] = ctk.StringVar(value="")
            resp_frame = ctk.CTkFrame(q_card, fg_color="transparent")
            resp_frame.grid(row=2, column=0, padx=34, pady=(0, 16), sticky="w")

            for opt_idx, option in enumerate(RESPONSE_OPTIONS):
                is_prefer = (option == "Prefer not to answer")
                btn = ctk.CTkRadioButton(
                    resp_frame,
                    text=option,
                    variable=self._responses[q["id"]],
                    value=option,
                    font=ctk.CTkFont(family="Segoe UI", size=12),
                    text_color=COLORS["text"] if not is_prefer else COLORS["muted"],
                    fg_color=cat_color,
                    hover_color=cat_color,
                    border_color=COLORS["border"],
                )
                btn.grid(row=0, column=opt_idx, padx=(0, 18), pady=2, sticky="w")

            row += 1

        # In-Slide Action Navigation Card
        next_cfg = SLIDES_CONFIG[slide_idx + 1]
        self._build_slide_nav_card(
            parent,
            row,
            slide_idx=slide_idx,
            next_label=f"Go to Next Slide: {next_cfg['short_title'].split('. ')[1]}  →",
            prev_label="← Previous Slide",
            helper_text=f"Completed {len(questions)} questions on {category}."
        )

    # -----------------------------------------------------------------------
    # Slide 4: Functional Assessment & Research Consent
    # -----------------------------------------------------------------------

    def _populate_slide_4(self, parent):
        row = 0
        cfg = SLIDES_CONFIG[4]

        # Slide Header Banner
        row = self._build_slide_banner(
            parent,
            row,
            icon=cfg["icon"],
            title="Slide 5 of 5: Functional Assessment & Research Consent",
            subtitle=cfg["subtitle"]
        )

        functional_questions = [q for q in SYMPTOM_QUESTIONS if q["category"] == "Functional"]
        cat_color = CATEGORY_COLORS["Functional"]

        for q_idx, q in enumerate(functional_questions):
            q_card = ctk.CTkFrame(
                parent,
                fg_color=COLORS["card"],
                corner_radius=10,
                border_width=1,
                border_color=COLORS["border"],
            )
            q_card.grid(row=row, column=0, padx=24, pady=(0, 10), sticky="ew")
            q_card.grid_columnconfigure(0, weight=1)

            header_row = ctk.CTkFrame(q_card, fg_color="transparent")
            header_row.grid(row=0, column=0, padx=20, pady=(14, 4), sticky="ew")
            header_row.grid_columnconfigure(1, weight=1)

            badge = ctk.CTkFrame(header_row, fg_color=cat_color, corner_radius=4, width=6, height=18)
            badge.grid(row=0, column=0, padx=(0, 8))
            badge.grid_propagate(False)

            ctk.CTkLabel(
                header_row,
                text=f"{q_idx + 1}.  {q['label']}",
                font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                text_color=COLORS["navy"],
                anchor="w",
            ).grid(row=0, column=1, sticky="w")

            ctk.CTkLabel(
                q_card,
                text=q["question"],
                font=ctk.CTkFont(family="Segoe UI", size=12),
                text_color=COLORS["text"],
                wraplength=860,
                justify="left",
                anchor="w",
            ).grid(row=1, column=0, padx=34, pady=(0, 12), sticky="w")

            self._responses[q["id"]] = ctk.StringVar(value="")
            resp_frame = ctk.CTkFrame(q_card, fg_color="transparent")
            resp_frame.grid(row=2, column=0, padx=34, pady=(0, 16), sticky="w")

            for opt_idx, option in enumerate(RESPONSE_OPTIONS):
                is_prefer = (option == "Prefer not to answer")
                btn = ctk.CTkRadioButton(
                    resp_frame,
                    text=option,
                    variable=self._responses[q["id"]],
                    value=option,
                    font=ctk.CTkFont(family="Segoe UI", size=12),
                    text_color=COLORS["text"] if not is_prefer else COLORS["muted"],
                    fg_color=cat_color,
                    hover_color=cat_color,
                    border_color=COLORS["border"],
                )
                btn.grid(row=0, column=opt_idx, padx=(0, 18), pady=2, sticky="w")

            row += 1

        # Research Consent Card
        consent_card = ctk.CTkFrame(
            parent,
            fg_color=COLORS["card"],
            corner_radius=12,
            border_width=1,
            border_color=COLORS["border"],
        )
        consent_card.grid(row=row, column=0, padx=24, pady=(4, 14), sticky="ew")
        consent_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            consent_card,
            text="✅  Research Consent & Voluntary Confirmation",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color=COLORS["navy"],
            anchor="w",
        ).grid(row=0, column=0, padx=20, pady=(16, 8), sticky="w")

        ctk.CTkLabel(
            consent_card,
            text=(
                "• I understand this assessment is for research documentation only, not a formal medical diagnosis.\n"
                "• All responses are stored strictly in local device database and not transmitted externally.\n"
                "• A qualified neurologist must independently evaluate structural MRI scans and clinical motor signs."
            ),
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=COLORS["text"],
            justify="left",
            anchor="w",
            wraplength=840,
        ).grid(row=1, column=0, padx=20, pady=(0, 12), sticky="w")

        self._consent_check = ctk.CTkCheckBox(
            consent_card,
            text="I have reviewed the information and agree to proceed with this evaluation",
            variable=self._consent_var,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=COLORS["navy"],
            fg_color=COLORS["cyan"],
            hover_color=COLORS["navy"],
            border_color=COLORS["border"],
        )
        self._consent_check.grid(row=2, column=0, padx=20, pady=(0, 18), sticky="w")

        row += 1

        # Final In-Slide Action Navigation Card
        self._build_slide_nav_card(
            parent,
            row,
            slide_idx=4,
            next_label="Save & Continue to MRI Upload  →",
            prev_label="← Previous Slide",
            is_final=True,
            helper_text="Final step: Saves assessment documentation and opens the MRI Upload pipeline."
        )

    # -----------------------------------------------------------------------
    # Common Slide Building Blocks
    # -----------------------------------------------------------------------

    def _build_slide_banner(self, parent, row: int, icon: str, title: str, subtitle: str) -> int:
        banner = ctk.CTkFrame(
            parent,
            fg_color=COLORS["card"],
            corner_radius=10,
            border_width=1,
            border_color=COLORS["border"],
        )
        banner.grid(row=row, column=0, padx=24, pady=(12, 12), sticky="ew")
        banner.grid_columnconfigure(1, weight=1)

        icon_label = ctk.CTkLabel(
            banner,
            text=icon,
            font=ctk.CTkFont(size=26),
            width=46,
            height=46,
        )
        icon_label.grid(row=0, column=0, rowspan=2, padx=(16, 12), pady=12)

        ctk.CTkLabel(
            banner,
            text=title,
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color=COLORS["navy"],
            anchor="w",
        ).grid(row=0, column=1, sticky="w", pady=(10, 0))

        ctk.CTkLabel(
            banner,
            text=subtitle,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=COLORS["muted"],
            anchor="w",
        ).grid(row=1, column=1, sticky="w", pady=(0, 10))

        return row + 1

    def _build_slide_nav_card(
        self,
        parent,
        row: int,
        slide_idx: int,
        next_label: str,
        prev_label: Optional[str] = None,
        is_final: bool = False,
        helper_text: str = ""
    ):
        """Single unified action card placed directly at the bottom of each slide content."""
        action_card = ctk.CTkFrame(
            parent,
            fg_color=COLORS["card"],
            corner_radius=12,
            border_width=1,
            border_color=COLORS["border"],
        )
        action_card.grid(row=row, column=0, padx=24, pady=(8, 28), sticky="ew")
        action_card.grid_columnconfigure(0, weight=1)
        action_card.grid_columnconfigure(1, weight=0)
        action_card.grid_columnconfigure(2, weight=0)
        action_card.grid_columnconfigure(3, weight=0)

        # Status / Helper text on left
        status_label = ctk.CTkLabel(
            action_card,
            textvariable=self._status_var,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=COLORS["muted"],
            anchor="w",
        )
        status_label.grid(row=0, column=0, padx=20, pady=16, sticky="w")
        if slide_idx == 0 or is_final:
            self._status_var.set(f"ℹ  {helper_text}")

        # Clear Form button
        ctk.CTkButton(
            action_card,
            text="Clear Form",
            width=100,
            height=40,
            corner_radius=8,
            fg_color="#FFF9E9",
            hover_color="#EAE5CC",
            border_width=1,
            border_color="#123F2D",
            text_color=COLORS["navy"],
            font=ctk.CTkFont(family="Segoe UI", size=12),
            command=self.reset,
        ).grid(row=0, column=1, padx=(0, 10), pady=14)

        # Previous button
        if prev_label:
            ctk.CTkButton(
                action_card,
                text=prev_label,
                width=140,
                height=40,
                corner_radius=8,
                fg_color="#FFF9E9",
                hover_color="#EAE5CC",
                border_width=1,
                border_color="#123F2D",
                text_color=COLORS["navy"],
                font=ctk.CTkFont(family="Segoe UI", size=13),
                command=self.go_to_prev_slide,
            ).grid(row=0, column=2, padx=(0, 10), pady=14)

        # Go to Next Slide / Proceed button
        next_btn = ctk.CTkButton(
            action_card,
            text=next_label,
            width=280 if not is_final else 290,
            height=40,
            corner_radius=8,
            fg_color=COLORS["cyan"] if is_final else COLORS["navy"],
            hover_color=COLORS["cyan_hover"] if is_final else "#1E543D",
            text_color="#FFF9E9",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            command=self._proceed if is_final else self.go_to_next_slide,
        )
        next_btn.grid(row=0, column=3, padx=(0, 20), pady=14)

    def _build_disclaimer(self, parent, row):
        disc = ctk.CTkFrame(
            parent,
            fg_color=COLORS["amber_bg"],
            corner_radius=10,
            border_width=1,
            border_color=COLORS["amber_border"],
        )
        disc.grid(row=row, column=0, padx=24, pady=(0, 14), sticky="ew")
        disc.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            disc,
            text="⚠  Research Screening Tool — Not a Formal Medical Diagnosis",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=COLORS["navy"],
            anchor="w",
        ).grid(row=0, column=0, padx=16, pady=(12, 4), sticky="w")

        ctk.CTkLabel(
            disc,
            text=(
                "These questions document exploratory cognitive, emotional, and motor symptoms for research analysis. "
                "They are not a replacement for a formal clinical neurological examination by a movement disorder specialist."
            ),
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=COLORS["text"],
            wraplength=840,
            justify="left",
            anchor="w",
        ).grid(row=1, column=0, padx=16, pady=(0, 12), sticky="w")

        return row + 1

    def _field_label(self, parent, text, row, col):
        ctk.CTkLabel(
            parent,
            text=text,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=COLORS["navy"],
            anchor="w",
        ).grid(row=row, column=col, padx=(0, 12), pady=(0, 4), sticky="w")

    def _build_instructions(self, parent, row):
        inst = ctk.CTkFrame(parent, fg_color=COLORS["cyan_light"], corner_radius=10, border_width=1, border_color=COLORS["border"])
        inst.grid(row=row, column=0, padx=24, pady=(0, 14), sticky="ew")
        inst.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            inst,
            text="📝  Assessment Instructions",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=COLORS["navy"],
            anchor="w",
        ).grid(row=0, column=0, padx=16, pady=(12, 4), sticky="w")

        ctk.CTkLabel(
            inst,
            text=(
                "• Over the next 4 slides, select the response that best describes symptom frequency over the past 4 weeks.\n"
                "• You can move back and forth between slides anytime using the 'Go to Next Slide' and 'Previous Slide' buttons.\n"
                "• Once all slides are complete, you can save and proceed directly to MRI brain scan analysis."
            ),
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=COLORS["text"],
            wraplength=840,
            justify="left",
            anchor="w",
        ).grid(row=1, column=0, padx=16, pady=(0, 12), sticky="w")

        return row + 1

    # -----------------------------------------------------------------------
    # Slide Navigation & Switching Logic
    # -----------------------------------------------------------------------

    def show_slide(self, index: int):
        """Display slide at given index (0 to 4)."""
        if index < 0 or index >= len(self._slide_frames):
            return

        # Hide all slides except the active one
        for i, frame in enumerate(self._slide_frames):
            if i == index:
                frame.pack(fill="both", expand=True)
            else:
                frame.pack_forget()

        # Scroll single canvas to top
        try:
            self._scroll._parent_canvas.yview_moveto(0)
        except Exception:
            pass

        self._current_slide_idx = index
        self._status_var.set("")

        # Update counter badge
        pct = int(((index + 1) / len(SLIDES_CONFIG)) * 100)
        self._slide_counter_badge.configure(text=f"Slide {index + 1} of {len(SLIDES_CONFIG)} ({pct}%)")

        # Update Stepper buttons styling
        for i, btn in enumerate(self._stepper_buttons):
            if i == index:
                btn.configure(
                    fg_color=COLORS["cyan"],
                    text_color="#FFF9E9",
                    font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                    border_color=COLORS["cyan"],
                )
            elif i < index:
                btn.configure(
                    fg_color=COLORS["green_light"],
                    text_color=COLORS["green"],
                    font=ctk.CTkFont(family="Segoe UI", size=12),
                    border_color=COLORS["border"],
                )
            else:
                btn.configure(
                    fg_color=COLORS["card"],
                    text_color=COLORS["muted"],
                    font=ctk.CTkFont(family="Segoe UI", size=12),
                    border_color=COLORS["border"],
                )

    def go_to_next_slide(self):
        """Advance to next slide with input validation."""
        curr = self._current_slide_idx

        # Validate Slide 0 (Demographics) before proceeding
        if curr == 0:
            age_str = self._age_var.get().strip()
            if not age_str:
                self._status_var.set("⚠  Please enter the patient's age before moving to the next slide.")
                return
            try:
                age = int(age_str)
                if not (1 <= age <= 120):
                    self._status_var.set("⚠  Please enter a valid age between 1 and 120.")
                    return
            except ValueError:
                self._status_var.set("⚠  Age must be a valid number.")
                return

        if curr < len(SLIDES_CONFIG) - 1:
            self.show_slide(curr + 1)
        else:
            self._proceed()

    def go_to_prev_slide(self):
        """Return to previous slide."""
        if self._current_slide_idx > 0:
            self.show_slide(self._current_slide_idx - 1)

    def jump_to_slide(self, index: int):
        """Allow direct jumping via stepper pill buttons."""
        self.show_slide(index)

    # -----------------------------------------------------------------------
    # Submission & Data Collection
    # -----------------------------------------------------------------------

    def reset(self):
        """Clear all form fields and return to slide 1."""
        self._age_var.set("")
        self._patient_code_var.set("")
        self._gender_var.set("Prefer not to say")
        self._consent_var.set(False)
        for var in self._responses.values():
            var.set("")
        self._status_var.set("")
        self.show_slide(0)

    def refresh(self):
        """Called when navigated to from main sidebar."""
        self.show_slide(self._current_slide_idx)

    def _validate(self) -> tuple[bool, str]:
        """Validate required fields before final upload transition."""
        age_str = self._age_var.get().strip()
        if not age_str:
            return False, "Please enter the patient's age on Slide 1."
        try:
            age = int(age_str)
            if not (1 <= age <= 120):
                return False, "Please enter a valid age between 1 and 120."
        except ValueError:
            return False, "Age must be a valid number."

        if not self._consent_var.get():
            return False, "Please check the research consent box on Slide 5 to proceed."

        answered = sum(1 for v in self._responses.values() if v.get())
        if answered == 0:
            return False, "Please answer at least one symptom question across the assessment slides."

        return True, ""

    def _collect_data(self) -> dict:
        """Build dictionary of demographic and symptom answers."""
        responses = {}
        for q in SYMPTOM_QUESTIONS:
            qid = q["id"]
            answer_text = self._responses.get(qid, ctk.StringVar()).get() or "Not answered"
            responses[qid] = {
                "label": q["label"],
                "category": q["category"],
                "answer": answer_text,
                "value": RESPONSE_VALUES.get(answer_text, -2),
            }

        age_str = self._age_var.get().strip()
        return {
            "patient_code": self._patient_code_var.get().strip(),
            "age": int(age_str) if age_str.isdigit() else None,
            "gender": self._gender_var.get(),
            "responses": responses,
            "completed_at": datetime.now().isoformat(),
            "total_questions": len(SYMPTOM_QUESTIONS),
            "answered_questions": sum(
                1 for r in responses.values() if r["answer"] not in ("Not answered", "Prefer not to answer")
            ),
        }

    def _proceed(self):
        """Validate, record data, and transition to MRI upload."""
        ok, err = self._validate()
        if not ok:
            self._status_var.set(f"⚠  {err}")
            # If consent or age is missing, navigate to relevant slide
            if "age" in err.lower():
                self.show_slide(0)
            elif "consent" in err.lower():
                self.show_slide(4)
            return

        self._status_var.set("")
        patient_data = self._collect_data()

        if hasattr(self.app_controller, "set_patient_data"):
            self.app_controller.set_patient_data(patient_data)

        logger.info(
            "Patient assessment completed: age=%s, answered=%d/%d questions",
            patient_data["age"],
            patient_data["answered_questions"],
            patient_data["total_questions"],
        )

        # Navigate to Upload screen
        self.app_controller.navigate_to("upload")

    def get_summary_text(self) -> str:
        """Return formatted plain-text summary of patient assessment."""
        data = self._collect_data()
        lines = [
            f"Patient Code : {data['patient_code'] or 'Not provided'}",
            f"Age          : {data['age'] or 'Not provided'}",
            f"Gender       : {data['gender']}",
            f"Completed    : {data['completed_at']}",
            "",
            "Symptom Responses by Category:",
        ]
        for cat in CATEGORIES:
            lines.append(f"\n  [{cat}]")
            for q in SYMPTOM_QUESTIONS:
                if q["category"] != cat:
                    continue
                r = data["responses"].get(q["id"], {})
                lines.append(f"    • {q['label']:<40} : {r.get('answer', 'Not answered')}")
        return "\n".join(lines)
