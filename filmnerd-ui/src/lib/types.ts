export type NarrativeTime = 'linear' | 'non_linear' | 'fragmented' | 'cyclical' | 'parallel'
export type PacingSignature = 'slow_burn' | 'measured' | 'propulsive' | 'frenetic' | 'variable'
export type ToneSignature = 'bleak' | 'melancholic' | 'deadpan' | 'absurdist' | 'earnest' | 'lyrical' | 'tense' | 'playful' | 'elegiac' | 'satirical'
export type RealityRegister = 'hyperrealist' | 'social_realist' | 'heightened_stylized' | 'magical_realist' | 'surrealist' | 'genre_artificial' | 'mythic'
export type MoralComplexity = 'clear_moral_poles' | 'sympathetic_antagonist' | 'morally_ambiguous' | 'protagonist_culpable' | 'systemic_no_villain' | 'nihilistic'
export type BodyExperience = 'dread_creeping' | 'tension_sustained' | 'catharsis_emotional' | 'wonder_awe' | 'discomfort_confrontational' | 'meditative_dissociative' | 'propulsive_momentum' | 'funny_uncomfortable' | 'grief_immersive'
export type ProductionRegister = 'microbudget_raw' | 'indie_crafted' | 'mid_budget_studio' | 'prestige' | 'blockbuster' | 'foreign_language_arthouse' | 'documentary_observational'
export type EndingValence = 'cathartic_resolved' | 'ambiguous_open' | 'bleak_closed' | 'hopeful_earned' | 'ironic_subverted' | 'transcendent' | 'abrupt_withholding'
export type DirectorLineage = 'european_art_cinema' | 'american_new_wave' | 'east_asian_modernism' | 'latin_american_realism' | 'mumblecore_naturalism' | 'genre_formalism' | 'documentary_hybrid' | 'postmodern_pastiche' | 'mainstream_classical' | 'south_asian_parallel' | 'african_diaspora' | 'independent_auteur' | 'transnational_global'
export type AnnotationConfidence = 'HIGH' | 'MEDIUM' | 'LOW'

export interface CraftAnnotation {
  tmdb_id: number
  title: string
  year: number | null
  poster_path: string | null
  narrative_time: NarrativeTime
  pacing_signature: PacingSignature
  point_of_view: string
  ending_valence: EndingValence
  tone_primary: ToneSignature
  tone_secondary: ToneSignature | null
  reality_register: RealityRegister
  moral_complexity: MoralComplexity
  character_legibility: string
  dialogue_density: 'near_silent' | 'sparse' | 'moderate' | 'dense'
  cinematographic_language: string
  colour_palette: string
  aspect_ratio: string
  score_style: string
  editor_signature: string
  world_building_depth: 'minimal' | 'light' | 'rich' | 'immersive'
  genre_subversion: 'none' | 'light' | 'moderate' | 'heavy'
  thematic_primary: string
  thematic_secondary: string | null
  director_lineage: DirectorLineage
  body_experience: BodyExperience
  production_register: ProductionRegister
  annotation_confidence: AnnotationConfidence
  user_rating: number | null
}

export interface TasteProfile {
  model_version: number
  best_model: string
  model_comparison: Record<string, { r2_mean: number; r2_std: number; mae_mean: number; mae_std: number }>
  trained_on_n_films: number
  variance_explained: number
  prediction_mae: number
  top_predictive_dimensions: string[]
  dimension_weights: Record<string, number>
  interpretable_dimensions: string[]
  ridge_dimension_weights: Record<string, number>
  divergence_profile: Record<string, Record<string, number>>
  low_signal_dimensions: string[]
  trained_at: string
  mean_user_rating: number
  rating_std: number
}

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  recommendations?: Recommendation[]
  timestamp: string
}

export interface Recommendation {
  tmdb_id: number
  title: string
  year: number
  poster_path: string | null
  explanation: string
  predicted_rating: number | null
  craft_dimensions: Partial<CraftAnnotation>
  knowledge_graph_path?: string[]
}

export interface FilmSearchResult {
  tmdb_id: number
  title: string
  year: number
  poster_path: string | null
  in_corpus: boolean
  annotation?: CraftAnnotation
}

export interface LogResult {
  tmdb_id: number
  title: string
  rating: number
  predicted_rating: number | null
  prediction_error: number | null
  is_new_film: boolean
}

export interface CorpusFilters {
  pacing_signature?: PacingSignature
  tone_primary?: ToneSignature
  body_experience?: BodyExperience
  reality_register?: RealityRegister
  moral_complexity?: MoralComplexity
  production_register?: ProductionRegister
  director_lineage?: DirectorLineage
  ending_valence?: EndingValence
  search?: string
}

export interface CorpusResponse {
  films: CraftAnnotation[]
  total: number
  page: number
  per_page: number
}
