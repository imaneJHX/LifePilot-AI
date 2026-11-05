export const studyAreas = [
  "Computer Science",
  "Data Science",
  "Business Analytics",
  "Engineering",
] as const;
export const countries = [
  "Germany",
  "Netherlands",
  "France",
  "Sweden",
  "Ireland",
  "Portugal",
];
export type StudyArea = (typeof studyAreas)[number];
export type Weights = {
  affordability: number;
  academic_fit: number;
  career_outlook: number;
  student_experience: number;
};
export const priorityLabels: Record<keyof Weights, string> = {
  affordability: "Affordability",
  academic_fit: "Academic alignment",
  career_outlook: "Career outlook",
  student_experience: "Student experience",
};
export interface ProfileInput {
  name: string;
  study_area: StudyArea;
  gpa: number;
  annual_budget_eur: number;
  countries: string[];
  goals: string;
  weights: Weights;
}
export interface Profile extends ProfileInput {
  id: string;
  created_at: string;
}
export interface Program {
  id: string;
  university: string;
  program: string;
  country: string;
  city: string;
  study_area: StudyArea;
  tuition_eur: number;
  living_cost_eur: number;
  duration_months: number;
  language: string;
  curriculum: string[];
  academic_index: number;
  career_index: number;
  experience_index: number;
  synthetic: true;
  provenance: string;
}
export interface RealProgram {
  id: string;
  university_name: string | null;
  program_name: string | null;
  country: string | null;
  city: string | null;
  official_university_url: string | null;
  official_program_url: string | null;
  degree_type: string | null;
  study_area: string | null;
  teaching_language: string | null;
  teaching_languages: string[] | null;
  tuition_fees: string | null;
  currency: string | null;
  academic_year: string | null;
  duration: string | null;
  duration_months: number | null;
  description: string | null;
  admission_requirements: string | null;
  english_language_requirements: string | null;
  application_deadline: string | null;
  application_opening_date: string | null;
  application_deadline_date: string | null;
  retrieval_date: string;
  verification_status: "unverified" | "needs_review" | "verified";
  deadline_status: "expired" | "upcoming" | "today" | "unknown";
  synthetic: false;
  recommendation_eligible: false;
}
export interface RealProgramCatalog {
  programs: RealProgram[];
  total: number;
  count: number;
  countries: string[];
  universities: string[];
  study_areas: string[];
  as_of_date: string;
  recommendation_eligible: false;
}
export interface Factor {
  criterion: keyof Weights;
  label: string;
  value: number;
  weight: number;
  ideal_distance_component: number;
  anti_ideal_distance_component: number;
  explanation: string;
}
export interface RankedProgram {
  rank: number;
  program: Program;
  score: number;
  annual_cost_eur: number;
  budget_remaining_eur: number;
  factors: Factor[];
}
export interface Recommendations {
  results: RankedProgram[];
  considered: number;
  excluded_over_budget: number;
  excluded_preferences: number;
  weights: Weights;
  methodology: string;
  disclaimer: string;
  synthetic: true;
}
export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}
export interface ChatResponse {
  message: ChatMessage;
  model: string;
  synthetic_context: true;
}
export const sampleProfile: ProfileInput = {
  name: "Alex",
  study_area: "Data Science",
  gpa: 3.5,
  annual_budget_eur: 25000,
  countries: [],
  goals:
    "Build a career in applied AI and find a program with a good balance of cost and academic depth.",
  weights: {
    affordability: 35,
    academic_fit: 30,
    career_outlook: 20,
    student_experience: 15,
  },
};
export const euro = (value: number) =>
  new Intl.NumberFormat("en-IE", {
    style: "currency",
    currency: "EUR",
    maximumFractionDigits: 0,
  }).format(value);
