# Task: Create Round 2 Data Processing Plan for TechArena Dashboard

## Objective
Develop a comprehensive plan for processing Round 2 data and implementing the Data Exploration Dashboard (View 1) based on the existing codebase structure.

## Background Context
This is a TechArena 2025 competition project that is transitioning from Round 1 to Round 2. The goal is to extend the existing data processing pipeline to handle Round 2 data and create visualization dashboards as specified in the project documentation.

## Design Philosophy: McKinsey Report Style
All Python visualizations and dashboard components must follow **McKinsey-style professional presentation standards**:

### Visual Design Principles
- **Clean and minimal**: Remove chart junk, unnecessary gridlines, and decorative elements
- **Professional color palette**: Use muted, business-appropriate colors (navy blues, grays, accent colors)
- **High data-ink ratio**: Maximize information, minimize non-data elements
- **Consistent formatting**: Uniform fonts, sizes, and spacing across all visualizations
- **Executive-friendly**: Clear takeaways, easy to scan, insights-driven

### Specific Requirements
- **Typography**: Clean sans-serif fonts (Arial, Helvetica, or similar)
- **Titles**: Clear, descriptive, action-oriented titles above each chart
- **Labels**: All axes clearly labeled with units
- **Legends**: Positioned thoughtfully, only when necessary
- **Colors**: 
  - Primary: Navy blue (#003f5c) or similar professional blue
  - Secondary: Grays for supporting data
  - Accent: One highlight color for key insights (e.g., teal #2f4b7c)
  - Avoid: Bright, neon, or childish colors
- **White space**: Generous margins and spacing between elements
- **Annotations**: Use sparingly to highlight key insights or anomalies

## Task Breakdown

### Phase 1: Understand the Existing Codebase (Analysis)
1. **Examine Round 1 Implementation**
   - Review all Python scripts in @py_script/ folder
   - Identify how Round 1 data from @data/TechArena2025_data.xlsx is:
     - Loaded and parsed
     - Transformed and cleaned
     - Stored (file formats, directory structure)
     - Visualized (libraries used, plot types, styling)
   - **Evaluate current visualization quality** against McKinsey standards
   - Note which visualizations need style improvements

2. **Study Project Requirements**
   - Read @doc/project_description.tex for overall project goals
   - Review @doc/official_instruction_docs/round2_intro_slides.md for Round 2 specifics
   - Compare data structure between:
     - @data/TechArena2025_data.xlsx (Round 1)
     - @data/TechArena2025_Phase2_data.xlsx (Round 2)
   - Document key differences in data schema, columns, and structure

3. **Understand Dashboard Requirements**
   - Carefully read @data_result_dashboard.md
   - Focus specifically on **Section 2: View 1 - Data Exploration Dashboard**
   - List all required visualizations, metrics, and interactive components
   - Note any data transformations needed for these visualizations

### Phase 2: Design the Plan (Synthesis)
Create a detailed plan document that includes:

1. **Data Loading Module**
   - Function specifications for loading Round 2 Excel data
   - Schema validation approach
   - Error handling strategy
   - JSON output structure and file naming convention
   - Where to save JSON files (directory structure)

2. **Data Transformation Module**
   - Required data cleaning steps
   - Feature engineering needs for Round 2
   - Data aggregation/grouping requirements
   - Comparison with Round 1 approach (what to reuse, what to modify)

3. **Visualization Module for View 1**
   - Break down each visualization from @data_result_dashboard.md Section 2
   - For each visualization specify:
     - Plot type (bar, line, scatter, heatmap, etc.)
     - Data source (which columns/features)
     - Python libraries to use (matplotlib, seaborn, plotly, etc.)
     - **McKinsey styling specifications**:
       - Color scheme for this specific chart
       - Font sizes and weights
       - Grid style (or removal)
       - Background color
       - Border and spine settings
     - Key parameters and styling
   - Code organization: suggest function names and module structure

4. **Styling Standards Module**
   - Create reusable styling templates/functions
   - Define a consistent theme that can be applied across all plots
   - Specify matplotlib rcParams or plotly templates
   - Color palette definitions (primary, secondary, accent colors)
   - Typography standards (font families, sizes for titles/labels/text)

5. **Implementation Roadmap**
   - Step-by-step implementation sequence
   - Dependencies between components
   - Estimated complexity for each component
   - Testing strategy

6. **View 2 Placeholder**
   - Add a TODO section for View 2 (post-Round 2 model)
   - Note what information will be needed once the model is built

## Deliverable Specification

**Output File**: @doc/dev_plan/plan_r2_data_process.md

**Required Sections**:
1. Executive Summary
2. Round 1 vs Round 2 Data Analysis
3. Data Loading Strategy
4. Data Processing Pipeline
5. **McKinsey-Style Visualization Standards** 
   - Color palette definitions
   - Typography specifications
   - Code templates for styling
   - Before/after examples if applicable
6. View 1 Implementation Plan (detailed breakdown)
7. Code Structure Recommendations
8. Implementation Timeline/Priority
9. TODO: View 2 (placeholder)
10. Open Questions/Risks

**Writing Style**:
- Clear, actionable language
- Use bullet points and numbered lists for clarity
- Include code snippets or pseudocode where helpful
- Reference specific files and line numbers when relevant
- Flag any ambiguities or assumptions
- **Include visualization mockups or style references** if helpful

## Execution Instructions
1. Start by reading and analyzing all referenced files using @ notation
2. Take notes on key patterns and structures
3. Research McKinsey-style visualization best practices
4. Draft the plan with concrete, implementable steps
5. Include specific code snippets for styling (matplotlib/seaborn/plotly themes)
6. Ensure the plan is self-contained and can be followed by another developer
7. Save the final plan to @doc/dev_plan/plan_r2_data_process.md

## Success Criteria
- [ ] All Round 2 data differences from Round 1 are documented
- [ ] Clear function signatures for data loading (input/output specifications)
- [ ] Every visualization from View 1 has an implementation approach
- [ ] **McKinsey-style visualization standards are clearly defined with code examples**
- [ ] **Reusable styling functions/templates are specified**
- [ ] Code reuse from Round 1 is maximized where appropriate
- [ ] The plan is detailed enough to start coding immediately after approval
- [ ] All visualizations will be professional, clean, and executive-ready