"""
lifestyle.py
============
Parkinson's Health & Lifestyle Guide Frame for Parkinova.
Provides practical, evidence-grounded educational information about:
- Indian food, nutrition, fiber, and hydration
- Medication and protein timing nuances
- Physical exercises, balance, and fall prevention
- Sample daily Indian meal plan (labeled as general educational example)
- Interactive preferences filter for tailored educational guidance

Strictly preserves Parkinova's Vintage Editorial palette and UI conventions.
"""

from __future__ import annotations

import customtkinter as ctk
from app.lifestyle_data import (
    INDIAN_FOOD_CATEGORIES,
    MEDICATION_PROTEIN_TIMING,
    EXERCISE_GUIDANCE,
    SAMPLE_INDIAN_MEAL_PLANS,
    SPECIALIZED_CONCERN_TIPS,
    LIFESTYLE_DISCLAIMER,
    get_personalized_lifestyle_guide,
)

PALETTE = {
    "bg": "#F5F0D8",               # Primary Background: Warm cream / vintage ivory
    "card": "#FFF9E9",             # Highlight Color: Warm off-white
    "primary": "#F0442E",          # Accent Color: Vibrant coral red
    "primary_hover": "#D43823",    # Slightly darker coral
    "primary_text": "#FFF9E9",     # Warm off-white
    "secondary": "#FFF9E9",        # Cream background for secondary buttons
    "secondary_border": "#123F2D", # Forest green border for secondary buttons
    "secondary_text": "#123F2D",   # Forest green text
    "secondary_hover": "#EAE5CC",  # Pale beige hover
    "text_dark": "#123F2D",        # Primary Text: Deep forest green
    "text_muted": "#365747",       # Secondary Text: Muted dark green
    "border": "#B8C4A5",           # Border Color: Muted sage green
    "callout_bg": "#EAE5CC",       # Subtle Background: Pale beige
    "warn": "#D77B65",             # Soft terracotta
}


class LifestyleFrame(ctk.CTkFrame):
    """
    Health & Lifestyle Educational Dashboard.
    """

    def __init__(self, parent, app_controller):
        super().__init__(parent, fg_color=PALETTE["bg"], corner_radius=0)
        self.app_controller = app_controller

        self.diet_var = ctk.StringVar(value="Vegetarian")
        self.concern_var = ctk.StringVar(value="General")

        self.build_ui()

    def build_ui(self):
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._build_header()
        self._build_content()

    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color=PALETTE["card"], corner_radius=0, height=70)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)

        inner = ctk.CTkFrame(header, fg_color="transparent")
        inner.pack(side="left", padx=32, pady=14)

        ctk.CTkLabel(
            inner,
            text="Parkinson's Health & Lifestyle Guide",
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            text_color=PALETTE["text_dark"],
        ).pack(side="left", padx=(0, 16))

        ctk.CTkLabel(
            inner,
            text="● Practical Education & Indian Nutrition",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=PALETTE["text_muted"],
        ).pack(side="left")

        # Bottom border
        ctk.CTkFrame(self, height=1, fg_color=PALETTE["border"]).grid(
            row=0, column=0, sticky="sew"
        )

    def _build_content(self):
        self.scroll = ctk.CTkScrollableFrame(self, fg_color=PALETTE["bg"], corner_radius=0)
        self.scroll.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        self.scroll.grid_columnconfigure(0, weight=1)

        # ── 1. Interactive Preference Card ──
        pref_card = ctk.CTkFrame(
            self.scroll,
            fg_color=PALETTE["card"],
            corner_radius=12,
            border_width=1,
            border_color=PALETTE["border"],
        )
        pref_card.pack(fill="x", padx=32, pady=(20, 12))

        pref_inner = ctk.CTkFrame(pref_card, fg_color="transparent")
        pref_inner.pack(fill="x", padx=20, pady=16)

        ctk.CTkLabel(
            pref_inner,
            text="Customize Educational Suggestions",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color=PALETTE["text_dark"],
        ).pack(anchor="w", pady=(0, 8))

        filters_row = ctk.CTkFrame(pref_inner, fg_color="transparent")
        filters_row.pack(fill="x")

        # Diet selector
        ctk.CTkLabel(
            filters_row,
            text="Diet / Cuisine:",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=PALETTE["text_dark"],
        ).pack(side="left", padx=(0, 8))

        diet_menu = ctk.CTkOptionMenu(
            filters_row,
            variable=self.diet_var,
            values=["Vegetarian", "Non_Vegetarian", "South_Indian", "North_Indian"],
            fg_color=PALETTE["secondary"],
            button_color=PALETTE["secondary_hover"],
            button_hover_color=PALETTE["border"],
            text_color=PALETTE["text_dark"],
            font=ctk.CTkFont(family="Segoe UI", size=12),
            command=self._on_preference_changed,
        )
        diet_menu.pack(side="left", padx=(0, 20))

        # Concern selector
        ctk.CTkLabel(
            filters_row,
            text="Primary Area of Focus:",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=PALETTE["text_dark"],
        ).pack(side="left", padx=(0, 8))

        concern_menu = ctk.CTkOptionMenu(
            filters_row,
            variable=self.concern_var,
            values=["General", "Constipation", "Medication_Timing", "Swallowing", "Fatigue"],
            fg_color=PALETTE["secondary"],
            button_color=PALETTE["secondary_hover"],
            button_hover_color=PALETTE["border"],
            text_color=PALETTE["text_dark"],
            font=ctk.CTkFont(family="Segoe UI", size=12),
            command=self._on_preference_changed,
        )
        concern_menu.pack(side="left", padx=(0, 20))

        # Focus Tips Banner
        self.focus_box = ctk.CTkFrame(
            pref_card,
            fg_color=PALETTE["callout_bg"],
            corner_radius=8,
            border_width=1,
            border_color=PALETTE["border"],
        )
        self.focus_box.pack(fill="x", padx=20, pady=(0, 16))

        self.focus_title = ctk.CTkLabel(
            self.focus_box,
            text="Targeted Health Insights",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=PALETTE["text_dark"],
            anchor="w",
        )
        self.focus_title.pack(fill="x", padx=14, pady=(10, 4))

        self.focus_text = ctk.CTkLabel(
            self.focus_box,
            text="",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=PALETTE["text_muted"],
            justify="left",
            wraplength=850,
        )
        self.focus_text.pack(fill="x", padx=14, pady=(0, 10))

        # ── 2. Medication & Protein Timing Card ──
        prot_card = ctk.CTkFrame(
            self.scroll,
            fg_color=PALETTE["card"],
            corner_radius=12,
            border_width=1,
            border_color=PALETTE["border"],
        )
        prot_card.pack(fill="x", padx=32, pady=(0, 16))

        ctk.CTkLabel(
            prot_card,
            text="💊  " + MEDICATION_PROTEIN_TIMING["title"],
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color=PALETTE["text_dark"],
        ).pack(anchor="w", padx=20, pady=(16, 6))

        ctk.CTkLabel(
            prot_card,
            text=MEDICATION_PROTEIN_TIMING["summary"],
            font=ctk.CTkFont(family="Segoe UI", size=12, slant="italic"),
            text_color=PALETTE["text_muted"],
            wraplength=850,
            justify="left",
        ).pack(anchor="w", padx=20, pady=(0, 10))

        for rule in MEDICATION_PROTEIN_TIMING["rules"]:
            r_frame = ctk.CTkFrame(prot_card, fg_color="transparent")
            r_frame.pack(fill="x", padx=20, pady=2)
            ctk.CTkLabel(
                r_frame,
                text="• ",
                font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                text_color=PALETTE["primary"],
            ).pack(side="left", anchor="n")
            ctk.CTkLabel(
                r_frame,
                text=rule,
                font=ctk.CTkFont(family="Segoe UI", size=11),
                text_color=PALETTE["text_dark"],
                wraplength=820,
                justify="left",
            ).pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(prot_card, text="").pack(pady=4)

        # ── 3. Indian Food Groups Grid ──
        food_header = ctk.CTkFrame(self.scroll, fg_color="transparent")
        food_header.pack(fill="x", padx=32, pady=(8, 4))
        ctk.CTkLabel(
            food_header,
            text="🥗  Indian Food Groups & Practical Examples",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color=PALETTE["text_dark"],
        ).pack(side="left")

        # 2-column grid of food categories
        grid_frame = ctk.CTkFrame(self.scroll, fg_color="transparent")
        grid_frame.pack(fill="x", padx=32, pady=(4, 16))
        grid_frame.grid_columnconfigure(0, weight=1)
        grid_frame.grid_columnconfigure(1, weight=1)

        for idx, cat in enumerate(INDIAN_FOOD_CATEGORIES):
            c_row = idx // 2
            c_col = idx % 2
            card = ctk.CTkFrame(
                grid_frame,
                fg_color=PALETTE["card"],
                corner_radius=10,
                border_width=1,
                border_color=PALETTE["border"],
            )
            card.grid(row=c_row, column=c_col, padx=8, pady=8, sticky="nsew")

            ctk.CTkLabel(
                card,
                text=cat["category"],
                font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                text_color=PALETTE["text_dark"],
            ).pack(anchor="w", padx=16, pady=(12, 4))

            ctk.CTkLabel(
                card,
                text=cat["benefits"],
                font=ctk.CTkFont(family="Segoe UI", size=10, slant="italic"),
                text_color=PALETTE["text_muted"],
                wraplength=380,
                justify="left",
            ).pack(anchor="w", padx=16, pady=(0, 6))

            for ex in cat["examples"]:
                ctk.CTkLabel(
                    card,
                    text=f"• {ex}",
                    font=ctk.CTkFont(family="Segoe UI", size=11),
                    text_color=PALETTE["text_dark"],
                    wraplength=380,
                    justify="left",
                ).pack(anchor="w", padx=16, pady=1)

            ctk.CTkLabel(card, text="").pack(pady=4)

        # ── 4. Sample Daily Indian Meal Plan Card ──
        self.meal_card = ctk.CTkFrame(
            self.scroll,
            fg_color=PALETTE["card"],
            corner_radius=12,
            border_width=1,
            border_color=PALETTE["border"],
        )
        self.meal_card.pack(fill="x", padx=32, pady=(0, 16))

        self.meal_title = ctk.CTkLabel(
            self.meal_card,
            text="🍛  Sample Indian Daily Meal Schedule (General Example)",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color=PALETTE["text_dark"],
        )
        self.meal_title.pack(anchor="w", padx=20, pady=(16, 4))

        ctk.CTkLabel(
            self.meal_card,
            text="Note: This is a general illustrative schedule. Individual needs, medication intervals, and allergies must be guided by a clinician.",
            font=ctk.CTkFont(family="Segoe UI", size=11, slant="italic"),
            text_color=PALETTE["text_muted"],
            wraplength=850,
            justify="left",
        ).pack(anchor="w", padx=20, pady=(0, 12))

        self.meal_items_frame = ctk.CTkFrame(self.meal_card, fg_color="transparent")
        self.meal_items_frame.pack(fill="x", padx=20, pady=(0, 16))

        # ── 5. Exercise, Daily Activities & Fall Safety ──
        ex_card = ctk.CTkFrame(
            self.scroll,
            fg_color=PALETTE["card"],
            corner_radius=12,
            border_width=1,
            border_color=PALETTE["border"],
        )
        ex_card.pack(fill="x", padx=32, pady=(0, 16))

        ctk.CTkLabel(
            ex_card,
            text="🏃  Exercise, Movement & Fall-Prevention Strategies",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color=PALETTE["text_dark"],
        ).pack(anchor="w", padx=20, pady=(16, 8))

        for ex in EXERCISE_GUIDANCE:
            e_box = ctk.CTkFrame(ex_card, fg_color=PALETTE["callout_bg"], corner_radius=8, border_width=1, border_color=PALETTE["border"])
            e_box.pack(fill="x", padx=20, pady=4)
            ctk.CTkLabel(
                e_box,
                text=ex["activity"],
                font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                text_color=PALETTE["text_dark"],
            ).pack(anchor="w", padx=12, pady=(8, 2))
            ctk.CTkLabel(
                e_box,
                text=ex["details"],
                font=ctk.CTkFont(family="Segoe UI", size=11),
                text_color=PALETTE["text_muted"],
                wraplength=820,
                justify="left",
            ).pack(anchor="w", padx=12, pady=(0, 8))

        ctk.CTkLabel(ex_card, text="").pack(pady=4)

        # ── 6. Regulatory Disclaimer ──
        disc_box = ctk.CTkFrame(
            self.scroll,
            fg_color=PALETTE["callout_bg"],
            corner_radius=8,
            border_width=1,
            border_color=PALETTE["border"],
        )
        disc_box.pack(fill="x", padx=32, pady=(0, 24))

        ctk.CTkLabel(
            disc_box,
            text="⚕️ Medical & Dietary Disclaimer",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=PALETTE["text_dark"],
        ).pack(anchor="w", padx=16, pady=(12, 4))

        ctk.CTkLabel(
            disc_box,
            text=LIFESTYLE_DISCLAIMER,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=PALETTE["text_muted"],
            wraplength=840,
            justify="left",
        ).pack(anchor="w", padx=16, pady=(0, 12))

        # Initial render of preference-based items
        self._update_rendered_guide()

    def _on_preference_changed(self, _val=None):
        self._update_rendered_guide()

    def _update_rendered_guide(self):
        diet = self.diet_var.get().lower()
        concern = self.concern_var.get().lower()

        guide = get_personalized_lifestyle_guide(diet, "all", concern)

        # Update Focus Tips
        self.focus_title.configure(text=f"Targeted Insights: {self.concern_var.get().replace('_', ' ')}")
        bullet_points = "\n".join([f"• {tip}" for tip in guide["concern_specific_tips"]])
        self.focus_text.configure(text=bullet_points)

        # Update Meal Schedule
        for widget in self.meal_items_frame.winfo_children():
            widget.destroy()

        meal_plan = guide["meal_plan"]
        for idx, item in enumerate(meal_plan):
            row_bg = PALETTE["callout_bg"] if idx % 2 == 0 else "transparent"
            item_frame = ctk.CTkFrame(self.meal_items_frame, fg_color=row_bg, corner_radius=6)
            item_frame.pack(fill="x", pady=2)

            ctk.CTkLabel(
                item_frame,
                text=item["meal"],
                font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                text_color=PALETTE["text_dark"],
                width=180,
                anchor="w",
            ).pack(side="left", padx=(10, 8), pady=6)

            ctk.CTkLabel(
                item_frame,
                text=item["item"],
                font=ctk.CTkFont(family="Segoe UI", size=11),
                text_color=PALETTE["text_muted"],
                wraplength=640,
                justify="left",
                anchor="w",
            ).pack(side="left", fill="x", expand=True, padx=(0, 10), pady=6)
