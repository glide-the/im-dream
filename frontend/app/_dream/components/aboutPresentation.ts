// [Input] Existing About page content and repository destination.
// [Output] Original team, release timeline and project copy shared by Web/native.
// [Pos] Static presentation data; no network request or release status is inferred.
type TeamMember = {
  name: string;
  role: string;
  description: string;
};

export const teamMembers: TeamMember[] = [
  {
    name: 'F2J',
    role: 'Creator & Developer',
    description: 'A solo developer exploring the intersection of AI, writing tools, and reflective thinking.'
  },
  {
    name: 'Sage',
    role: 'Creator & Designer',
    description: 'A designer with a keen eye for aesthetics and user experience, bringing thoughtful design to the intersection of AI and reflective writing.'
  },
  {
    name: 'glide-the',
    role: 'Contributor',
    description: "Contributes to Ink & Memory's development and product iteration."
  }
];

export const developmentTimeline=[
              {
                version: 'v1.0.0',
                date: 'Oct 2025',
                title: 'Project Start',
                description: 'Core writing interface with voice commentary system'
              },
              {
                version: 'v1.1.0',
                date: 'Oct 2025',
                title: 'Voice Customization',
                description: 'Added settings panel for customizing voice personas'
              },
              {
                version: 'v1.2.0',
                date: 'Oct 2025',
                title: 'Energy Pool System',
                description: 'Introduced weighted character counting and energy-based triggering'
              },
              {
                version: 'v1.3.0',
                date: 'Oct 2025',
                title: 'Calendar & Analysis',
                description: 'Added calendar view for memory browsing and analysis tools'
              }
            ];
export const ABOUT_REPOSITORY_URL='https://github.com/shuxueshuxue/ink-and-memory';
export const ABOUT_SUMMARY='A reflective writing companion that helps you capture thoughts and memories';
export const ABOUT_DESCRIPTION=[
  'Ink & Memory is an experimental writing tool that brings multiple "voices" to your writing process. As you write, AI-powered personas inspired by Disco Elysium provide commentary, insights, and alternative perspectives on your thoughts.',
  "The system analyzes your writing in real-time and generates contextual comments from different archetypal voices—Logic, Empathy, Drama, Rhetoric, and more. These voices don't just respond to what you write; they help you think differently about it.",
] as const;
