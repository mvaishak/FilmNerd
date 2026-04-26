"""
film_schema.py
Film Taste Intelligence Engine — Canonical Schema
--------------------------------------------------
All enums and dataclasses used across the annotation pipeline,
taste decomposition model, knowledge graph, and prediction engine.

Annotation source:  GPT-4o via Instructor structured outputs
Storage:            Qdrant (craft annotations) + NetworkX (knowledge graph)
                    + SQLite (prediction ground truth)
Ground truth:       Letterboxd CSV export + TMDB enrichment
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


# ─────────────────────────────────────────────
# SECTION 1 — NARRATIVE & STRUCTURE
# ─────────────────────────────────────────────

class NarrativeTime(str, Enum):
    """Temporal organisation of the story as presented on screen."""
    LINEAR        = "linear"
    NON_LINEAR    = "non_linear"
    FRAGMENTED    = "fragmented"
    CYCLICAL      = "cyclical"
    PARALLEL      = "parallel"       # multiple simultaneous timelines


class PacingSignature(str, Enum):
    """Overall rhythm at which the film moves — not genre, but felt tempo."""
    SLOW_BURN    = "slow_burn"       # deliberate, accumulative
    MEASURED     = "measured"        # unhurried but purposeful
    PROPULSIVE   = "propulsive"      # momentum-driven, forward pull
    FRENETIC     = "frenetic"        # relentless, overwhelming
    VARIABLE     = "variable"        # pacing itself is a formal device


class PointOfViewStrategy(str, Enum):
    """
    Whose perspective organises the film's narration and audience alignment.
    Annotate based on who the camera privileges, not marketing framing.
    """
    SINGLE_PROTAGONIST     = "single_protagonist"      # tight alignment with one character
    ENSEMBLE_DISTRIBUTED   = "ensemble_distributed"    # no stable centre of gravity
    UNRELIABLE_SUBJECTIVE  = "unreliable_subjective"   # narration is actively misleading
    OMNISCIENT_DETACHED    = "omniscient_detached"     # camera knows more than any character
    OBSERVER_WITNESS       = "observer_witness"        # peripheral character watching events
    COLLECTIVE_WE          = "collective_we"           # community or group as protagonist


class EndingValence(str, Enum):
    """
    Emotional and narrative register of the film's resolution.
    Annotate the ending as experienced, not as marketed.
    """
    CATHARTIC_RESOLVED   = "cathartic_resolved"    # emotionally complete closure
    AMBIGUOUS_OPEN       = "ambiguous_open"         # deliberately withholds resolution
    BLEAK_CLOSED         = "bleak_closed"           # resolved but without hope
    HOPEFUL_EARNED       = "hopeful_earned"         # optimism that the film has justified
    IRONIC_SUBVERTED     = "ironic_subverted"       # resolution undercuts expectations
    TRANSCENDENT         = "transcendent"           # moves beyond emotional resolution
    ABRUPT_WITHHOLDING   = "abrupt_withholding"     # cut off before resolution arrives


# ─────────────────────────────────────────────
# SECTION 2 — TONE & REGISTER
# ─────────────────────────────────────────────

class ToneSignature(str, Enum):
    """
    Dominant emotional register. Use the primary tone; secondary tones
    captured in tone_secondary (List[ToneSignature] on the annotation object).
    """
    BLEAK        = "bleak"
    MELANCHOLIC  = "melancholic"
    DEADPAN      = "deadpan"
    ABSURDIST    = "absurdist"
    EARNEST      = "earnest"
    LYRICAL      = "lyrical"
    TENSE        = "tense"
    PLAYFUL      = "playful"
    ELEGIAC      = "elegiac"         # grief-tinged, retrospective
    SATIRICAL    = "satirical"


class RealityRegister(str, Enum):
    """
    The film's relationship to realism — distinct from world-building depth.
    A Dardennes film and a Lanthimos film are both minimal world-building
    but occupy completely different registers.
    """
    HYPERREALIST        = "hyperrealist"         # more real than real (Dardennes, early Cassavetes)
    SOCIAL_REALIST      = "social_realist"       # grounded, observational, socio-political
    HEIGHTENED_STYLIZED = "heightened_stylized"  # real world, artificial register
    MAGICAL_REALIST     = "magical_realist"      # the impossible intrudes without comment
    SURREALIST          = "surrealist"           # logic of dreams, not causality
    GENRE_ARTIFICIAL    = "genre_artificial"     # embraces its own constructed artifice
    MYTHIC              = "mythic"               # operating at the scale of fable or archetype


class MoralComplexity(str, Enum):
    """
    How the film positions characters and events on a moral axis.
    Annotate based on the film's stance, not genre convention.
    """
    CLEAR_MORAL_POLES      = "clear_moral_poles"      # good and evil are legible
    SYMPATHETIC_ANTAGONIST = "sympathetic_antagonist"  # villain has grounded motivation
    MORALLY_AMBIGUOUS      = "morally_ambiguous"       # the film refuses to adjudicate
    PROTAGONIST_CULPABLE   = "protagonist_culpable"    # hero's actions are indicted
    SYSTEMIC_NO_VILLAIN    = "systemic_no_villain"     # harm is structural, not personal
    NIHILISTIC             = "nihilistic"              # moral framework is absent or mocked


# ─────────────────────────────────────────────
# SECTION 3 — CHARACTER & PERFORMANCE
# ─────────────────────────────────────────────

class CharacterLegibility(str, Enum):
    """
    Whether characters are meant to be psychologically understood.
    A major taste axis: some viewers need coherent interiority;
    others are drawn to behavioural opacity (Bresson, Haneke, Kaurismäki).
    """
    TRANSPARENT_PSYCHOLOGICAL = "transparent_psychological"  # motivation is clear and full
    BEHAVIORIST_OPAQUE        = "behaviorist_opaque"         # actions without explanation
    SYMBOLIC_ARCHETYPAL       = "symbolic_archetypal"        # character as idea
    CONTRADICTORY_UNSTABLE    = "contradictory_unstable"     # intentional inconsistency
    SOCIALLY_DETERMINED       = "socially_determined"        # character as product of system


class DialogueDensity(str, Enum):
    """Volume and narrative load carried by spoken language."""
    NEAR_SILENT = "near_silent"   # dialogue is exceptional or absent
    SPARSE      = "sparse"        # largely visual storytelling
    MODERATE    = "moderate"
    DENSE       = "dense"         # dialogue is the primary vehicle


# ─────────────────────────────────────────────
# SECTION 4 — VISUAL CRAFT
# ─────────────────────────────────────────────

class CinematographicLanguage(str, Enum):
    """
    The dominant visual grammar of the film.
    Annotate the cinematographer's primary mode, not every technique used.
    """
    HANDHELD_INTIMATE  = "handheld_intimate"   # proximity, instability, presence
    STATIC_COMPOSED    = "static_composed"     # frames held, architecture deliberate
    LONG_TAKE          = "long_take"           # duration as the primary unit
    MONTAGE_DRIVEN     = "montage_driven"      # meaning through collision of cuts
    EXPRESSIONISTIC    = "expressionistic"     # image distorted toward inner state
    OBSERVATIONAL      = "observational"       # camera as witness, not participant
    FORMALIST          = "formalist"           # visual system takes precedence


class ColourPalette(str, Enum):
    """
    The dominant chromatic strategy of the film.
    Annotate the intentional palette, not accidental production choices.
    """
    DESATURATED_MUTED    = "desaturated_muted"    # drained, grey-shifted
    HIGH_CONTRAST_STARK  = "high_contrast_stark"  # hard blacks, high exposure
    NATURALISTIC         = "naturalistic"          # colours as found, not graded
    WARM_SATURATED       = "warm_saturated"        # amber, gold, heat
    COOL_CLINICAL        = "cool_clinical"         # blue, grey, institutional
    EXPRESSIONIST_BOLD   = "expressionist_bold"    # colour as emotional signal
    MONOCHROME           = "monochrome"            # black and white, intentional
    PERIOD_AUTHENTIC     = "period_authentic"      # palette serves historical recreation


class AspectRatio(str, Enum):
    """
    The framing ratio of the film. Use the primary/dominant ratio.
    Annotate the intended exhibition ratio, not streaming crop.
    """
    ACADEMY_133        = "academy_133"         # 1.33:1 — classic, boxy, intimate
    EUROPEAN_166       = "european_166"        # 1.66:1 — mid-century European art cinema
    WIDESCREEN_185     = "widescreen_185"      # 1.85:1 — standard modern widescreen
    ANAMORPHIC_239     = "anamorphic_239"      # 2.39:1 — scope, cinematic spectacle
    SCOPE_235          = "scope_235"           # 2.35:1 — older anamorphic
    SQUARE_11          = "square_11"           # 1:1 — social media era, intentional constraint
    VERTICAL_916       = "vertical_916"        # 9:16 — vertical/portrait, rare
    VARIABLE           = "variable"            # ratio shifts as a formal device


# ─────────────────────────────────────────────
# SECTION 5 — SOUND & MUSIC
# ─────────────────────────────────────────────

class ScoreStyle(str, Enum):
    """Character of the film's musical score or its deliberate absence."""
    ORCHESTRAL    = "orchestral"
    ELECTRONIC    = "electronic"
    AMBIENT       = "ambient"
    JAZZ          = "jazz"
    FOLK_ACOUSTIC = "folk_acoustic"
    MINIMAL       = "minimal"        # sparse motifs, long silences
    ABSENT        = "absent"         # no score; diegetic sound only
    ECLECTIC      = "eclectic"       # licensed tracks, varied sourcing


class EditorSignature(str, Enum):
    """
    The dominant editing mode — how the film constructs time through cuts.
    This is about rhythm and structure, not pace (see PacingSignature).
    """
    CLASSICAL_INVISIBLE  = "classical_invisible"   # continuity editing; cuts unnoticed
    RHYTHMIC_EXPRESSIVE  = "rhythmic_expressive"   # cuts timed to music or emotion
    ELLIPTICAL           = "elliptical"            # time is compressed or skipped
    ASSOCIATIVE_MONTAGE  = "associative_montage"   # cuts create conceptual meaning
    ABRUPT_DISRUPTIVE    = "abrupt_disruptive"     # cuts that interrupt and unsettle
    LONG_TAKE_MINIMAL    = "long_take_minimal"     # editing withheld; duration is the choice


# ─────────────────────────────────────────────
# SECTION 6 — WORLD & GENRE
# ─────────────────────────────────────────────

class WorldBuildingDepth(str, Enum):
    """
    How much the film asks the viewer to accept and inhabit a constructed world.
    Distinct from RealityRegister — a social-realist film can have minimal
    world-building; a fantasy film can have immersive world-building.
    """
    MINIMAL   = "minimal"     # realistic setting, no world-building required
    LIGHT     = "light"       # a few rules or departures from reality
    RICH      = "rich"        # world has history, texture, and internal logic
    IMMERSIVE = "immersive"   # the world itself is the primary subject


class GenreSubversion(str, Enum):
    """How far the film uses genre as a vehicle for something it is not."""
    NONE     = "none"       # plays genre entirely straight
    LIGHT    = "light"      # minor genre departures
    MODERATE = "moderate"   # genre expectations are regularly undermined
    HEAVY    = "heavy"      # genre is a delivery mechanism; the film is elsewhere


# ─────────────────────────────────────────────
# SECTION 7 — THEMES & LINEAGE
# ─────────────────────────────────────────────

class ThematicCluster(str, Enum):
    """Primary thematic territory. A film may occupy more than one; use thematic_secondary."""
    IDENTITY_SELF         = "identity_self"
    POWER_SYSTEMS         = "power_systems"
    GRIEF_LOSS            = "grief_loss"
    MEMORY_TIME           = "memory_time"
    BELONGING_EXILE       = "belonging_exile"
    VIOLENCE_CONSEQUENCE  = "violence_consequence"
    LOVE_INTIMACY         = "love_intimacy"
    SURVIVAL              = "survival"
    FAITH_MEANING         = "faith_meaning"
    CLASS_INEQUALITY      = "class_inequality"
    TECHNOLOGY_HUMANITY   = "technology_humanity"
    COMING_OF_AGE         = "coming_of_age"
    BODY_TRANSFORMATION   = "body_transformation"
    JUSTICE_COMPLICITY    = "justice_complicity"


class DirectorLineage(str, Enum):
    """
    The cinematic tradition the film most clearly belongs to.
    Annotate based on formal and philosophical alignment, not nationality alone.
    """
    EUROPEAN_ART_CINEMA    = "european_art_cinema"
    AMERICAN_NEW_WAVE      = "american_new_wave"
    EAST_ASIAN_MODERNISM   = "east_asian_modernism"
    LATIN_AMERICAN_REALISM = "latin_american_realism"
    MUMBLECORE_NATURALISM  = "mumblecore_naturalism"
    GENRE_FORMALISM        = "genre_formalism"
    DOCUMENTARY_HYBRID     = "documentary_hybrid"
    POSTMODERN_PASTICHE    = "postmodern_pastiche"
    MAINSTREAM_CLASSICAL   = "mainstream_classical"
    SOUTH_ASIAN_PARALLEL   = "south_asian_parallel"
    AFRICAN_DIASPORA       = "african_diaspora"
    INDEPENDENT_AUTEUR     = "independent_auteur"
    TRANSNATIONAL_GLOBAL   = "transnational_global"  # no clean national/tradition home


# ─────────────────────────────────────────────
# SECTION 8 — VIEWING EXPERIENCE
# ─────────────────────────────────────────────

class BodyExperience(str, Enum):
    """
    The dominant somatic/emotional experience of watching.
    Two films can share tone labels but produce entirely different felt experiences.
    Annotate what watching it is like, not what it is about.
    """
    DREAD_CREEPING            = "dread_creeping"
    TENSION_SUSTAINED         = "tension_sustained"
    CATHARSIS_EMOTIONAL       = "catharsis_emotional"
    WONDER_AWE                = "wonder_awe"
    DISCOMFORT_CONFRONTATIONAL= "discomfort_confrontational"
    MEDITATIVE_DISSOCIATIVE   = "meditative_dissociative"
    PROPULSIVE_MOMENTUM       = "propulsive_momentum"
    FUNNY_UNCOMFORTABLE       = "funny_uncomfortable"
    GRIEF_IMMERSIVE           = "grief_immersive"


class ProductionRegister(str, Enum):
    """
    Material texture and production context of the film.
    Not a quality judgment — a descriptor of the mode of making.
    Useful for taste modelling since viewers often have strong implicit preferences here.
    """
    MICROBUDGET_RAW           = "microbudget_raw"
    INDIE_CRAFTED             = "indie_crafted"
    MID_BUDGET_STUDIO         = "mid_budget_studio"
    PRESTIGE                  = "prestige"
    BLOCKBUSTER               = "blockbuster"
    FOREIGN_LANGUAGE_ARTHOUSE = "foreign_language_arthouse"
    DOCUMENTARY_OBSERVATIONAL = "documentary_observational"


# ─────────────────────────────────────────────
# SECTION 9 — CORE ANNOTATION OBJECT
# ─────────────────────────────────────────────

class CraftAnnotation(BaseModel):
    """
    The canonical annotation object for a single film.
    Produced by the Craft Dimension Annotator (GPT-4o + Instructor).
    Stored in Qdrant indexed by tmdb_id.

    Fields marked # COMPUTED are not LLM-annotated — they are derived
    from external data sources and written by the ingestion pipeline.

    All List[...] fields allow multi-value annotation where a single
    enum would lose signal. For regression purposes, these are one-hot
    expanded in the taste decomposition model.
    """

    # ── Identity (from Letterboxd + TMDB) ──────────────────────
    tmdb_id:          int
    title:            str
    year:             Optional[int] = None
    runtime_minutes:  Optional[int] = None             # COMPUTED — from TMDB
    original_language: Optional[str] = None            # COMPUTED — ISO 639-1 code from TMDB

    # ── Craft dimensions (LLM-annotated) ────────────────────────
    narrative_time:          NarrativeTime
    pacing_signature:        PacingSignature
    point_of_view:           PointOfViewStrategy
    ending_valence:          EndingValence

    tone_primary:            ToneSignature
    tone_secondary:          list[ToneSignature] = Field(default_factory=list)  # [] if tone is singular
    reality_register:        RealityRegister
    moral_complexity:        MoralComplexity

    character_legibility:    CharacterLegibility
    dialogue_density:        DialogueDensity

    cinematographic_language: CinematographicLanguage
    colour_palette:          ColourPalette
    aspect_ratio:            AspectRatio

    score_style:             ScoreStyle
    editor_signature:        EditorSignature

    world_building_depth:    WorldBuildingDepth
    genre_subversion:        GenreSubversion

    thematic_primary:        ThematicCluster
    thematic_secondary:      list[ThematicCluster] = Field(default_factory=list)  # [] if one cluster dominates
    director_lineage:        DirectorLineage

    body_experience:         BodyExperience
    production_register:     ProductionRegister

    # ── User signal (from Letterboxd export) ────────────────────
    user_rating:             Optional[float] = None    # 0.5–5.0; None if unrated
    user_review_text:        Optional[str] = None      # None if no review logged
    watch_date:              Optional[str] = None      # ISO 8601 date string

    # ── Computed divergence fields ───────────────────────────────
    # COMPUTED — populated by ingestion pipeline, not LLM annotator
    letterboxd_avg_rating:   Optional[float] = None    # 0.5–5.0 Letterboxd aggregate
    metacritic_score:        Optional[int] = None      # 0–100; None if unavailable
    critical_divergence:     Optional[float] = None    # user_rating minus letterboxd_avg_rating
                                                       # positive = user rates above consensus
                                                       # negative = user rates below consensus

    # ── Annotation metadata ──────────────────────────────────────
    annotation_model:        str = "gpt-4o"            # model version used to annotate
    annotation_version:      int = 1                   # schema version for consistency audits
    annotation_confidence:   int = Field(ge=1, le=3, default=2)
    confidence_note:         Optional[str] = None


# ─────────────────────────────────────────────
# SECTION 10 — KNOWLEDGE GRAPH NODE TYPES
# ─────────────────────────────────────────────

class CrewRole(str, Enum):
    """
    The five crew node types in the cinematic knowledge graph.
    Actors are excluded — attribution is too fragmented for craft-level modelling.
    See spec section 6: Key Technical Decisions.
    """
    DIRECTOR        = "director"
    CINEMATOGRAPHER = "cinematographer"
    EDITOR          = "editor"
    WRITER          = "writer"
    COMPOSER        = "composer"


class GraphEdgeType(str, Enum):
    """
    Typed relationship edges in the NetworkX knowledge graph.
    INFLUENCED_BY and THEMATIC_LINK are drawn from curated seed data
    and LLM-derived craft annotation similarity.
    COLLABORATED_WITH is derived directly from shared TMDB credits.
    """
    COLLABORATED_WITH = "collaborated_with"   # shared film credit
    INFLUENCED_BY     = "influenced_by"       # directional aesthetic lineage
    THEMATIC_LINK     = "thematic_link"       # shared thematic cluster across films


# ─────────────────────────────────────────────
# SECTION 11 — PREDICTION & EVALUATION
# ─────────────────────────────────────────────

@dataclass
class PredictionRecord:
    """
    Written to SQLite by the Prediction Engine for every recommended unseen film.
    Ground truth is populated by the Rating Ground Truth Logger CLI
    after the user watches the film and logs their actual rating.
    MAE is computed by the Evaluation Framework across all completed records.
    """
    tmdb_id:              int
    title:                str
    predicted_rating:     float                 # 0.5–5.0, generated by gpt-4o-mini
    actual_rating:        Optional[float]       # populated post-watch; None until logged
    prediction_error:     Optional[float]       # abs(predicted - actual); None until logged
    taste_model_version:  int                   # version of taste model used at prediction time
    predicted_at:         str                   # ISO 8601 timestamp
    watched_at:           Optional[str]         # ISO 8601 timestamp; None until logged
    top_dimensions_used:  list[str]             # craft dimensions with highest weight at prediction time


@dataclass
class TasteProfile:
    """
    Output of the Taste Decomposition Model.
    Summarises which craft dimensions most reliably predict the user's ratings
    and where they systematically diverge from critic and audience consensus.
    Passed as context to the Recommendation Agent and Prediction Engine.
    """
    model_version:            int
    trained_on_n_films:       int
    top_predictive_dimensions: list[str]        # ranked by regression coefficient magnitude
    variance_explained:       float             # R² of regression against user ratings
    divergence_profile:       dict[str, float]  # dimension → mean divergence from consensus
    low_signal_dimensions:    list[str]         # dimensions with insufficient rating variance
    trained_at:               str               # ISO 8601 timestamp


# ─────────────────────────────────────────────
# SECTION 12 — CONFIDENCE & DEGRADATION FLAGS
# ─────────────────────────────────────────────

class AnnotationConfidence(str, Enum):
    """
    Set by the Craft Dimension Annotator based on available context.
    Films with sparse criticism coverage receive LOWER confidence;
    used by the RAG layer to decide fallback behaviour (spec risk R3).
    """
    HIGH    = "high"    # rich criticism corpus coverage, unambiguous annotation
    MEDIUM  = "medium"  # some coverage; minor annotation uncertainty
    LOW     = "low"     # sparse context; annotation may be unreliable


class TasteModelConfidence(str, Enum):
    """
    Emitted by the Prediction Engine based on rated history size.
    Triggers hedged language in recommendation explanations (spec test T04).
    """
    INSUFFICIENT = "insufficient"   # < 50 rated films; model not trustworthy
    DEVELOPING   = "developing"     # 50–149 films; model forming
    ESTABLISHED  = "established"    # 150–299 films; regression meaningful
    MATURE       = "mature"         # 300+ films; taste model stable