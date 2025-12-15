# OWLIN UI DESIGN CONTRACT — DO NOT IGNORE  

You must reference and apply these design rules for every UI element you create or modify in this project.  

These rules override Tailwind defaults and override any assumptions you normally make when generating components.  

If a user asks for a UI element, you must design it according to this contract automatically.

-------------------------------------------------------------

## GLOBAL VISUAL LANGUAGE

-------------------------------------------------------------

• Tone: calm, professional, non-alarming.

• Use Owlin colours:

  - Desaturated Navy: #2B3A55

  - Sage Green: #7B9E87

  - Soft Grey: rgba(0,0,0,0.08)

  - No pure black or pure white. Use softened variants.

• Typography: Inter or Work Sans only.

• Font weights:

  - 600 = section titles  

  - 500 = labels  

  - 400 = body text  

• Iconography:

  - Lucide icons  

  - monoline stroke  

  - 16px inline / 20–24px structural  

• No harsh reds or loud colours unless critical.

-------------------------------------------------------------

## LAYOUT RULES

-------------------------------------------------------------

• Everything follows a 12-column responsive grid.

• Page padding = 24px minimum.

• Section spacing = 24–32px.

• Split layout pages:

  - Left column: fixed 360–420px scrollable.

  - Right column: flexible detail panel.

• All content must breathe: avoid crowding.

-------------------------------------------------------------

## CARD COMPONENT RULES (MANDATORY)

-------------------------------------------------------------

• Base card: white background, 4–6px rounded corners.

• Border: 1px solid rgba(0,0,0,0.05).

• Shadow: ultra-soft (0 1px 2px rgba(0,0,0,0.04)).

• Internal padding: 16–20px.

• Header:

  - Left = primary identifier  

  - Right = date/status/chevron  

  - Title font-size: 15–16px  

• Status/metadata row:

  - confidence badge  

  - page count  

  - matched/unmatched  

• Spacing inside card follows 8pt system: 8/12/16px.

• Expandable content:

  - 150–200ms smooth ease-out  

  - no bounce, no jitter  

  - consistent width  

-------------------------------------------------------------

## FORMS

-------------------------------------------------------------

• Inputs:

  - rounded 6px  

  - border: 1px solid rgba(0,0,0,0.08)  

  - background: off-white  

  - focus: border-color #3A5A87 + subtle outline  

• Use two-column layout where appropriate.

• Buttons:

  - Primary: navy or sage, white text, 12px radius  

  - Secondary: soft grey background  

  - Never full-width except mobile  

-------------------------------------------------------------

## TABLES

-------------------------------------------------------------

• Header row:

  - light grey background  

  - uppercase labels 11–12px  

• Row height: 40–48px.

• Row hover: rgba(0,0,0,0.03).

• No heavy vertical borders.

• Empty state: icon + calm text.

-------------------------------------------------------------

## GRAPHS

-------------------------------------------------------------

• Primary line: Owlin navy.

• Secondary: soft green.

• Tooltips: rounded, soft shadow, quiet.

• Grid lines: ultra-light rgba(0,0,0,0.05).

• Hover interactions must be smooth, no jitter.

-------------------------------------------------------------

## BADGES

-------------------------------------------------------------

• Badge height: 16–18px.

• Rounded pill.

• Soft background colours:

  - Green: rgba(123,158,135,0.15)

  - Amber: rgba(255,165,0,0.15)

  - Red: rgba(255,90,90,0.12) (critical only)

  - Grey: rgba(0,0,0,0.08)

• Text always muted (no harsh red/green).

-------------------------------------------------------------

## SPACING & RHYTHM

-------------------------------------------------------------

• Follow strict 8pt grid:

  - 8px micro  

  - 16px element  

  - 24px section  

• Cards: top/bottom 16px, header/content 12px.

• Never compress UI elements to fill space.

-------------------------------------------------------------

## MOTION RULES

-------------------------------------------------------------

• Animation timing: 150–250ms ease-out.

• No aggressive spring physics.

• Use fades for entrances, not overshoots.

• Expand/collapse must feel light and controlled.

-------------------------------------------------------------

## ERROR & FEEDBACK

-------------------------------------------------------------

• No pop-ups unless absolutely necessary.

• Use inline quiet text for validation errors.

• Allow tooltips for clarity, never alarmist red.

-------------------------------------------------------------

## ENFORCEMENT BEHAVIOUR

-------------------------------------------------------------

Whenever you generate React/TSX/Tailwind code:

- You MUST apply these rules automatically.

- You MUST justify any deviation explicitly.

- If the user requests something that violates the Owlin rules, gently restyle it to match Owlin unless they insist.

- All components must look visually consistent with existing Owlin UI.

-------------------------------------------------------------

## OUTPUT FORMAT

-------------------------------------------------------------

When writing new UI components for Owlin:

1. Provide full, complete TSX file(s)

2. Include Tailwind classes that conform to the Owlin design contract

3. Explain briefly how each part aligns with the contract

4. Avoid placeholder-looking UI; always create polished, production-ready designs.

