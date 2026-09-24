# Changelog

All notable changes to HyperTrace (formerly LMU App) are documented here.

---

## [1.4.0]

### Assetto Corsa

- **Assetto Corsa is the third supported game.** The original Assetto
  Corsa — not Competizione, not EVO — detected live like the other two,
  with its own presets and its own class colours. Speed and gear, pedals,
  Delta, fuel and weather read your car straight from the game and need
  nothing installed.
- **Standings and Relative need the in-game app.** Assetto Corsa shares
  nothing about the other cars, so a small HyperTrace app runs inside the
  game and passes the field along. Copy the `AssettoCorsa\apps` folder
  from this archive into your Assetto Corsa folder, switch HyperTrace on
  in the game's app list, and leave its window open. It needs Custom
  Shaders Patch. Without it every other overlay still works and the two
  boards simply stay empty.
- **The Tyres overlay works on Assetto Corsa**, with live wear and
  temperatures for your own car. Wear is read from Custom Shaders Patch,
  which measures it against the car's own tyres, so a car whose tyres last
  a long way reads as barely worn after a handful of corners — as it
  should. Each tyre is also coloured against the temperature it actually
  wants to be at, rather than one figure assumed for every car.
- **The Battery overlay works on Assetto Corsa** for the cars with a
  hybrid system, and stays empty for the many that have none.
- **Cars that publish their own data are read too.** Modern mods carry far
  more than Assetto Corsa's own telemetry, and HyperTrace reads what a car
  publishes — starting with its state of charge, which for some cars the
  game's own gauge gets wrong.
- **You make your own car classes.** Assetto Corsa has none, so the
  Presets page has an "Arrange car classes…" button that opens a window of
  its own: every car you have driven on the left, the classes you name on
  the right, and you drag a car onto a class to file it there. The bin
  forgets a car; the cross on its tag takes it out of its class. Cars you
  leave out share one group, and each class can have its own preset,
  exactly like Le Mans Ultimate's categories.
- Standings shows those classes by their **full name** on the group badge,
  rather than shortening them the way it does the games' own class codes —
  they are your words.
- Gaps between cars are read off your own quickest lap, as they already
  are on iRacing, so a car beside you on track reads as beside you on the
  board.
- The race board is ordered on where the cars actually are, not on a
  position that only updates at the line.

### Class colours

- **Every class gets a colour of its own.** iRacing's classes and Assetto
  Corsa's were all drawn in the same grey, which made a multi-class board
  hard to read at a glance. A class with no colour of its own is now
  handed one, and no two classes on track are handed the same. Le Mans
  Ultimate's categories keep the colours they have always had.
- Settings has **four class colours** to choose from, used in that order.
- The pencil beside a class on the Presets page picks that one class's
  colour outright, and DEFAULT gives the automatic one back. On Assetto
  Corsa the same pencil, in the car class window, sets both its name and
  its colour — and there you may give two classes the same colour if you
  want to.

### Fuel and Energy calculators

- **"REFUEL as pit-exit total"**, a new tick box for Le Mans Ultimate in
  both calculators. LMU's pit screen asks for the level you drive OUT of
  the pits with, while REFUEL says how much to put in — so the figure on
  screen had to be added to what was already in the car before it could be
  typed in. Ticked, REFUEL shows the level to leave with, ready to copy
  straight across.
- **The laps either side of a pit stop no longer count.** The lap you come
  in on and the lap you leave on are driven at pit speed, not racing pace,
  and averaging them in quietly moved the figure the whole stop is planned
  from. Both calculators now leave them out on their own, and LAST holds
  the most recent proper lap rather than following you through the stop.
- **No stop is called for a lap that will never be driven.** With enough
  fuel to reach the flag but not enough to also cover the safety margin,
  the calculators still asked for a few litres — for a lap beyond the end
  of the race. The margin now steps aside once the race can be finished
  without it.

### Standings and Relative

- **The LMU Standings layout shows the gap between you and each car, not a
  track relative.** The figure took whichever way round the lap was
  nearer, which meant a car on its way to lapping you sat a few seconds
  behind you on the road while holding most of a lap on you — and read as
  a car comfortably held off. A car ahead of you now always reads
  negative, one behind always positive, whichever way round you meet, and
  a lap or more apart the seconds give way to -1L or +2L.
- **Relative shows penalties too.** The tag Standings has always carried
  — SG, DT, added seconds — now hangs off Relative's edge as well, on the
  same two settings: whether to show it, and which side it sits on. The
  car about to serve a drive-through is often the one right beside you,
  which is the overlay you are looking at when it matters. Le Mans
  Ultimate only, the one game that publishes penalties.
- **Relative: a car a lap apart from you is coloured the moment it is
  beside you.** The row's colour — red for a car lapping you, blue for one
  you are lapping — was decided on how far apart the two of you were in
  race distance, and only once that passed nine tenths of a lap. Two cars
  a lap apart running close together are nowhere near that, so the colour
  went missing exactly where it matters: alongside a backmarker you are
  about to lap, or alongside the car coming past to take a lap off you.
  Most of all with the start/finish line between you, where the car that
  has just crossed it carries a whole lap more than the one that has not,
  though the two are side by side. The colour now reads the laps each car
  has completed together with how far round the current one it sits, and
  which side of you its row is on — so a car genuinely a lap apart is
  coloured wherever it is, and one merely far ahead on your own lap is
  not. Both simulators.

### Fixes

- **Le Mans Ultimate's shared memory is read the way its September update
  asks for.** The game now announces each new frame in two steps instead
  of one, and waiting for both, in that order, is what the update says
  makes a frame safe to read. The app kept working after the update and
  still does either way; this closes the window where a frame could be
  read while the game was part-way through writing it.
- **"Launch with Windows" survives a refused write and a moved app.** The
  switch failed silently where Windows would not let the entry be written,
  and an app that had been moved or reinstalled left Windows launching a
  path that no longer existed while the option still looked on. The entry
  is now put right when the app has moved, and the switch says so when it
  cannot be set.
- **Icons are drawn sharply at any display scaling.** At fractional
  scaling — 125%, 150% — the small icons were drawn at one size and
  rescaled to another, and came out muddy; the bin in particular was hard
  to recognise. Every icon is now drawn at the size it appears, and the
  bin has been redrawn.
- **Stream mode follows a change of game.** Switching games while
  streaming left the broadcast overlays showing the previous game's
  columns — blank, and impossible to turn off — until HyperTrace was
  restarted. The desktop overlays already followed the switch; the
  streamed ones now do too.

---

## [1.3.2]

### Fixes

- **iRacing: the overlays no longer vanish during the last lap of a timed
  race.** The moment the clock reached its full length — 15:00 of 15:00 —
  the session's elapsed time stopped moving, and a clock that stands still
  reads as a paused game: every overlay was hidden for the rest of the
  lap, on the desktop and in Stream mode alike, coming back only once the
  session ended. The clock now keeps counting past the end of the
  countdown, as Le Mans Ultimate's own does, so the overlays stay up to
  the flag.
- **iRacing: the gaps and Relative are measured on your own lap.** Every
  car's position around the lap came from iRacing's estimate for its
  model, which is close but not exact: against what the cars on track
  actually did, the figures were out by 0.18 to 0.70 s on average
  depending on the circuit. From your second clean lap of a session, the
  app uses the lap you have just driven as the ruler instead, which brings
  that to 0.05 to 0.08 s — and a car a few centimetres ahead of another is
  now always shown ahead of it. Until that lap exists, iRacing's own
  estimate still does the job.
- **iRacing: Relative and the standings put the cars around you on the
  right side again.** A class like GT3 mixes car models that iRacing paces
  separately, and the position figures it publishes are expressed through
  each car's own pace — so two GT3s side by side could read up to half a
  second apart, and a car level with you could show as ahead of you (on a
  double-file grid, the car beside you read 0.2 s ahead). 1.3.1 removed the
  correction that puts every car on your pace, believing a single class
  shared one; it is back, for every car, in every kind of field.
- **iRacing: positions move the moment a car is passed.** They only
  changed as cars crossed the start/finish line, because the position
  iRacing publishes is official timing, updated at the line. While a race
  is running, the order now comes from where each car actually is on the
  road. On the grid and after the chequered flag, the official order still
  stands, and so does the best-lap order in practice and qualifying.
- **A car level with the one ahead of it no longer shows a lap's gap.** On
  an iRacing grid, with P1 and P2 side by side in double file and P2 a hair
  ahead on track, P2's gap to the leader read 120 seconds: the gap added a
  whole lap whenever the car it was measured against sat fractionally
  behind, a rule only meant for a leader that has just crossed the line.
  Whether that lap belongs is now judged on how far round the race each car
  actually is, and a car level with or ahead of its reference shows no gap.
- **iRacing: the gap and interval columns are live again, and a change of
  leader no longer zeroes the gap.** 1.3.1 took them from iRacing's own
  time behind the leader, which turned out to be official timing too:
  refreshed only at the line, so both columns stood still for a lap at a
  time, and a new leader left the gap at zero until the next crossing. They
  are measured from each car's position on the road again, as before 1.3.1.
- **iRacing: a car being towed no longer climbs the order.** The running
  order ranks cars on where they are around the lap, and a tow puts a car
  in its pit box at once — so one towed to a box further round the lap
  than where it stopped gained places while sitting there, motionless. It
  now keeps the place it held on track until it drives off again.
- **iRacing: a car starting from the pit lane stays behind the field.** It
  waits at pit exit, which is past the start/finish line, and iRacing
  credits it a lap as the field crosses that line — seen in a recorded
  race, with the car stationary in its box. Counted as further round the
  lap than everyone still short of pit exit, it was shown leading at the
  green. It now sits behind every car that has taken the start until it
  joins the track.
- **The standings' figures are readable at a glance.** Gaps and intervals
  changed on every frame, which made a column of digits to decipher
  rather than read while driving. They now refresh once a second. The
  board itself is still drawn every frame, so rows sliding to their new
  places and the best-lap highlights are as smooth as before.
- **The standings no longer cut the bottom driver in half.** When a car
  retired from the middle of the order, everyone below it slid up a row
  while the board lost one — and for the length of that movement the row
  on its way out was drawn past the bottom edge of the panel, showing as
  half a driver. Reported on a full field in the LMU layout.
- **Le Mans Ultimate: Delta's sector colours are right.** Purple was
  handed out where green was due, mostly in sectors 1 and 2. A rival's
  sector only counted once their whole lap was finished, so a quicker one
  set on the lap under way was not yet known when yours was graded — and
  none of it counted at all while the Delta overlay was hidden (auto-hide
  in the garage, or the overlay switched off). Sector times are now taken
  for every car the moment each sector is completed, whether the overlay
  is on screen or not, and a sector's time is only read once the game has
  confirmed it belongs to the lap being timed. Best sectors also belong to
  one session now: they used to carry over from practice or qualifying
  into the race, which left the board calling a genuine session best
  merely green.
- **A car a hair ahead of you reads "-0.0", not "-+0.0".** A gap that
  small rounds to zero, and Relative was printing the rounded figure's own
  plus sign after the minus. The fuel and virtual-energy reference figures
  had the same flaw.
- **No "L0" or "L-1" badge on the grid.** The pit badge names the lap a
  car pitted on, and before the first crossing there is no such lap: cars
  starting from the pits carried "L0" in Le Mans Ultimate and "L-1" in
  iRacing for the rest of the session. A stop with no completed lap behind
  it is no longer labelled.
- **Quitting a game no longer switches the app to the other one.** Closing
  iRacing sent the app back to Le Mans Ultimate — the game last picked in
  the header — and loaded LMU's preset over the overlays, though LMU had
  never been launched, taking any unsaved change to the iRacing layout
  with it. The app now stays on the game you just quit, overlays and all,
  until another game starts or you pick one in the header. Launching with
  no game running still opens on your pick, as before.
- **Launching HyperTrace with a game already running shows that game's
  overlays.** Opened after iRacing, the app kept Le Mans Ultimate's
  overlay positions and settings on screen, with only the LMU-only parts
  switched off. The game's own preset was only ever loaded when the app
  saw the game change, and a game that is already running when the app
  starts never does. The app now remembers which game the layout on
  screen belongs to, and loads the running game's preset whenever the two
  differ. Relaunching into the game you last played changes nothing, so a
  layout you tweaked without saving is still there.
- **iRacing: Delta compares you with this session's best lap.** It was
  measuring against your best ever lap in that car at that track — a
  record iRacing keeps between sessions — so a fresh race opened already
  being judged against a lap set some other day, and the bar never moved
  however the session went. It now resets with the session, which is what
  the same overlay has always done in Le Mans Ultimate.

---

## [1.3.1]

### Standings — two new layouts

- **"LMU Standings' layout"** turns the board into the game's own, in
  HyperTrace's styling: position, manufacturer, driver, a single timing
  figure, tires and virtual energy. In a race that figure is the gap
  relative to you; in practice and qualifying it is the gap to the
  leader, to three decimals, with the leader showing their own best lap
  instead. In any session, a driver's figure becomes their last lap for a
  few seconds when they cross the line — how many seconds is up to you.
- **The mode decides its own columns**, so the column list and the
  per-column switches step aside while it is on: it is LMU's board, and
  anything that would make it something else is simply not offered. What
  stays yours: how many drivers are listed and which, everything in the
  header, names, the player-row highlight, opacity, size and font size.
- **"Cycling columns"** stops the board from showing every column at
  once. You choose which stay put and which take turns in a single slot
  on the right, and how long each turn lasts — ten seconds by default.
  The changeover slides the old column out and the new one in, and those
  two seconds are added to the time you set rather than taken out of it,
  so a column is never on screen for less than you asked.
- The two are one choice — **Standard, LMU Standings' layout, or Cycling
  columns** — and picking one puts the other away.

### Standings — columns

- **One list decides which columns appear, in what order, and how precise
  each one is.** Choosing what to show and arranging it used to be
  separate controls in separate places, which meant a column you had
  turned off still sat in the order list doing nothing. Each row now
  carries its own checkbox, and the five columns with a decimal setting
  carry that too, labelled.
- **Every column can be switched off**, position, manufacturer logo,
  driver name and status badge included. They are compulsory only under
  the LMU layout, which fixes the whole set.
- **Status badges — PIT, OUT, GAR — appear in the LMU layout** as well.
- On your own row, a gap to yourself is shown as a dash rather than a
  zero.

### Overlay settings

- **The four overlays with the most settings now have tabs** — Layout,
  Content, Names, Visual — instead of one long column. Standings,
  Relative and both calculators. The others are short enough to read as
  they are and were left alone. A few settings changed neighbourhood in
  the process: alternate-row shading and the best-lap highlight are under
  Visual, how many drivers are listed is under Content, and "Player row"
  is now Visual, Player highlight. Nothing you had set has changed.
- **A search box** finds a setting across every tab when you know what
  you are after.
- **Sections fold**, so a long list of settings can be put away rather
  than scrolled past. They start open: a settings window without tabs is
  one because it is short, and there was nothing to put away there.
- **"Revert changes"** puts an overlay back exactly as it was when you
  opened its settings — every change applies live, and this is the undo
  for an evening of experimenting that went nowhere. It lights up only
  once there is something to undo. It is not "Reset to defaults", which
  is still there and still throws everything away.
- **The preview shows the overlay at its real size** whatever your
  Windows display scaling is set to, and the settings window fits on
  screen at 125% and above instead of running off the right edge.
- **A few settings that could not explain themselves in a label now
  say what they do** when you hover them: the fuel and energy safety
  margins, the AVG 5 reset, and the two Standings durations.
- **The settings window has been redrawn.** It draws its own title bar
  now, with the app mark and a breadcrumb, instead of printing its name
  in the Windows caption and again as a heading inside itself. The
  preview sits on a stage of its own, and the buttons, switches, steppers
  and dropdowns were all redrawn to match the overlays they configure.
- **Choosing a layout shows you the layout**: Standard, LMU Standings'
  and Cycling columns are three cards with a small drawing of what each
  one does to the board, instead of three stacked buttons.
- **The preview can be seen against a plain grid** as well as a track
  photo — the photo answers "how will this read over the game", the grid
  answers "what exactly am I drawing". It is a way of looking, not a
  setting: nothing about it is saved.
- **The footer says how much you have changed** — "3 unsaved changes"
  beside Revert changes — and the session switches moved there as pills,
  across the window, since they apply to the whole overlay rather than
  to any one tab.
- **The column list says how many columns are on** on its own header
  (11/11), so a folded list still answers whether something was switched
  off, and a column switched off fades but keeps its place in the order.

### The app window

- **The window has been redrawn.** It draws its own title bar — the app
  mark, the wordmark and the version — instead of printing its name in
  the Windows caption, and both images are drawn at their exact pixel
  size, so they stay sharp whatever your display scaling is set to.
- **It keeps one height** whichever view you are on, instead of growing
  and shrinking every time you click something in the sidebar.
- **The overlays list says how many are on**, on its own header, and each
  row is one line: the name, its settings, its switch.
- **The lock and the game selector sit together above the list**, and say
  which state you are in — "UNLOCKED, drag overlays to reposition them" —
  rather than leaving it to a button's label.
- **The preset bar moved into the footer**, where it belongs to the
  window rather than to the overlays list, and **it says when you have
  unsaved changes**: anything a preset stores counts, whether it is a
  switch here, a setting inside an overlay's own window, or an overlay
  dragged across the screen.

### Presets, stream and settings

- **The presets view says how many presets you have**, on its own
  header, and **the folder they live in is one click away**. A preset
  tied to a car class now carries that class's colour, so a list of them
  can be read at a glance.
- **The stream view says whether it is live** on its own header: LIVE,
  OFF, or PORT IN USE when something else already has the port, with the
  detail in the tooltip. It used to be a line of text under the port
  field, reading like a caption for it.
- **The list of overlays to stream says how many are on**, and while
  streaming is off, everything under the master switch is greyed and
  inert rather than offering eleven controls that do nothing. Copying an
  overlay's browser-source address is an icon on its row now, not a
  button spelling out "URL".
- **The settings page reads as rows**: what the setting is called, what
  it currently does underneath that, and the control on the right —
  where the label used to change along with the setting.
- **Every window and dialog now shares one look**, down to the prompt
  that asks whether closing should quit or minimise to the tray, and the
  window that copies an overlay's settings into other presets.

### Visibility in session

- **The Practice, Qualifying and Race switches now work.** They have been
  in every overlay's settings for some time, remembering what you chose
  and doing nothing with it. An overlay is now shown or hidden according
  to the session you are in, per overlay, so a board you want in the race
  and a fuel calculator you want in practice can each say so. Nothing is
  hidden while no game is running — that stays Auto-hide's job.
- **The same switches work for streamed overlays**, with their own
  answers, kept apart from the ones on your own screen.
- They sit pinned under the settings rather than among them, reachable
  whichever tab you are on.

### Appearance

- **The bar across the top of each overlay can be switched off, and
  recolored.** Both live on the Settings page rather than in each
  overlay's own settings: it is one look shared by all of them, so it is
  set once.
- **The accent color is now its own setting, and repaints everything
  amber in the app** — the gear indicator on Pedals and Speed & Gear, the
  headings and highlights across the interface, not just the bar. The
  color picker is the same one used everywhere else, with a Default
  button to go back to the original amber. Existing setups are untouched
  until you change it.
- **Text on buttons reads more cleanly.** The shadow under it was near
  enough black to be an outline, which looked different on every
  background it fell on; it is now light enough to simply darken whatever
  is behind it.

### Fixes

- **Delta no longer paints a sector purple while you are losing time on
  it.** Purple was measured against each rival's *last* lap rather than
  the best they had managed all session, so a rival pitting or stuck in
  traffic lowered the bar enough for a mediocre sector to clear it — and
  your own earlier laps were left out of the comparison entirely, which
  let a sector slower than your own best be called the best in the class.
  Purple now means quicker than every rival and no slower than yourself.
- **On your own on track, an improvement is purple again.** With nobody
  else having run the sector, the quickest it has been run this session
  is yours, which is what purple says.
- **iRacing: the session clock counts the session, not your evening.**
  Both halves of it were measured from the moment you entered rather than
  from the start of the session, so a fifteen-minute race could go green
  already reading four minutes gone and eleven left — whatever you had
  spent waiting. Elapsed and remaining now both come from the session's
  own countdown. Until a race starts, elapsed still shows how long you
  have been sitting there, and goes to zero at the green flag.
- **iRacing: the gap and interval columns agree with the game's own
  timing.** Both were rebuilt from where each car sat round the lap, a
  reconstruction of something iRacing already times — and one that moved
  with the cars' speeds rather than with the racing. They now come from
  iRacing's own time behind the leader. Le Mans Ultimate is unaffected:
  it publishes no such figure, and its boards work as they did.
- **Relative: a car sits on one side of you, not on both.** Every car was
  measured twice, once as a gap ahead and once as a gap behind, and which
  figure you were shown came down to how many rows each side happened to
  have spare — so the same car could read as most of a lap ahead or as a
  little behind. It now gets one signed gap and one row.
- **iRacing: Relative shows the sim's own figures, untouched.** They were
  being stretched onto your own class's pace so that cars of every class
  shared one clock, and that stretching moved the numbers around as much
  as the racing did. They are now iRacing's estimates as they come, which
  is what its other overlays compare. In a multiclass field this makes a
  gap to another class approximate — nothing at the start/finish line,
  growing to the difference between the two classes' lap times by the end
  of the lap. Single-class racing is unaffected, and so is Le Mans
  Ultimate.
- **Relative: crossing the line no longer unsettles the gaps.** Whether
  you and another car are on opposite sides of the start/finish line is
  now judged on where you both are on track, rather than inferred from
  the time between you, which took a guessed lap time to be right.
- **iRacing: the starting order is right on the grid.** Before the field
  crossed the line for the first time, iRacing had not yet placed anyone,
  and the board fell back on no order at all — it only came right on that
  first crossing. It now uses the session's own classification, and
  failing that the grid from qualifying, until live timing takes over.
- **iRacing: a race with no time limit no longer claims to last a week.**
  Lap-limited races carry iRacing's "unlimited" marker instead of a
  length, and the header was showing it as 168:00:00.
- **The car class badge grows with the font size.** Everything else in
  a class header followed it — the badge's own width, and its text — so
  raising the size left the badge behind, at the height it has always
  had, beside rows that had all grown around it. At the default size it
  is unchanged, so no board you have set up moves.
- **No more stray preset for a game you have not opened.** At startup,
  before the game had connected, HyperTrace could create a preset for
  whichever game the header happened to be showing, holding the other
  game's layout — visible as a preset changing on its own a second after
  launch. Existing presets were never touched by this, and none are
  touched now.

---

## [1.3.0]

### iRacing

- **iRacing is now supported**, alongside Le Mans Ultimate. HyperTrace
  notices which of the two is running and switches to it on its own —
  nothing to set, no restart, and it follows you if you close one and
  launch the other. While neither is running, the game picker in the
  header decides whose settings and presets you're looking at.
- **Overlays available on iRacing**: Speed & Gear, Pedals, Delta,
  Standings, Relative, Weather, Fuel Calculator and Battery. The battery
  gauge reads the hybrid state of charge on cars that have one, and sits
  at zero on cars that don't — like every overlay, it is shown or hidden
  by its own on/off switch and nothing else.
- **Three overlays are hidden on iRacing** rather than shown empty:
  Damage, because iRacing publishes none of it; Tyres, because its wear
  and temperature readings only refresh in the pits and are useless on
  track; and the VE Calculator, because iRacing has no virtual energy at
  all. All three come back by themselves in LMU.
- **Standings hides its LMU-only columns on iRacing** — VE/Fuel, tire
  compound and penalties, none of which iRacing publishes per opponent.
  Position, laps, gap, interval, best and last lap, delta and pit status
  all work for the whole field.
- **Weather shows current conditions only on iRacing** — air and track
  temperature, rain and wetness. iRacing publishes no forecast of any
  kind, so that section is dropped entirely and the panel shrinks to fit
  rather than leaving an empty strip.

### Stream

- **Stream mode is back.** Each overlay is served as a live web page you
  can add to OBS (or anything else with a browser source), restoring the
  feature the previous Python app had. The Stream page in the sidebar has
  a master switch, the port, and one row per overlay with its own
  settings, a button to copy its URL, and its own on/off. Overlays are
  off for streaming until you switch them on — turning streaming on does
  not immediately publish everything you have on your own screen.
- **Stream overlays have their own settings**, separate from the ones on
  your screen. That is the point of the feature: a broadcast usually
  wants different sizes and columns from what the driver is reading
  mid-corner. They start from the defaults rather than copying your
  desktop layout.
- **They keep their transparency**, so they composite straight over your
  video with no green screen and no matte.
- **A separate "hide when not driving"** for the stream, independent of
  the desktop overlays' own. Hidden means the overlay goes transparent on
  air, not that the feed stops.
- **Note that this opens a port on your machine**: while streaming is on,
  the overlays are reachable from your local network, not only from this
  PC. That is what lets OBS run on a second machine, and it matches how
  the Python app worked.

### Presets

- **Presets are now kept separately for each game.** A layout is only
  meaningful for the game it was built for, so LMU and iRacing each have
  their own list, and names only have to be unique within a game — an
  LMU "Race" and an iRacing "Race" are two different presets. Switching
  game switches presets with it. Your existing presets all become LMU's,
  automatically, on first launch.
- **New "Apply to…" button in every overlay's settings.** Tune an
  overlay once, then copy just that overlay's settings into any of your
  other presets — including the other game's, and into the stream
  overlays — with tick-all shortcuts per game and overall. It leaves
  every other overlay in those presets untouched, and deliberately does
  not carry across whether the overlay is switched on, or where it sits,
  unless you tick the box for the position: which overlays are on and
  where they are is most of what makes one preset different from another.
- **"Preset per class" now works on iRacing.** The panel used to list
  LMU's five fixed categories, which is meaningless against iRacing's
  hundreds of car classes. On iRacing it now lists the classes you have
  actually raced, remembered as you drive them, with a ✕ to drop any row
  you no longer want (it comes back if you drive that class again). LMU
  keeps its five categories exactly as before.
- **Lock is no longer part of a preset.** Whether the overlays are pinned
  in place is a setting in its own right now, so loading a layout never
  quietly makes them draggable again — which matters more than it used to,
  since presets now load themselves on a game switch and on a class
  change.

### Standings

- **Multiclass boards are easier to follow.** Each class is now separated
  by a gap, and a line in that class's own colour runs from its badge all
  the way to the panel's right edge — the badge alone marked the boundary
  only at the far left, which is no help when your eye is on the gap or
  lap-time columns. The line is shaped into the badge rather than butting
  against it, so the two read as one marker.
- **The header can show time remaining** instead of elapsed / total, for
  when that is the only figure you want.
- **Positions now slide to their new place** instead of jumping when the
  order changes, using the same easing as the settings dialog's column
  reordering. Each row moves independently, which is what makes an
  overtake read as one; a car appearing for the first time is placed
  directly rather than sliding in from somewhere it never was.
- **Taking the best lap of your class sweeps a soft purple band down that
  car's Best cell**, and down Last as well while that is the lap in
  question. It is deliberately faint and brief — this marks a moment on a
  board you read at a glance, so it has to register without becoming
  something to look at. Only the class best is marked; a personal best
  that leaves someone else ahead is not.
- **Best and Last are centred** in their columns rather than left-aligned.
- **Every number has fixed-width digits** — position, gap, interval, best,
  last and delta. Montserrat's digits are not all the same width, so lap
  times and gaps visibly jittered as their digits changed. Punctuation
  keeps its natural width; only the digits are given uniform slots.
- **Values sit further from their column edge**, and the position column
  is tighter against the panel edge and the car logo.
- **Every other row is shaded**, very faintly, so the eye can hold a line
  across a wide board. The banding restarts at each class, and your own
  row keeps its own highlight rather than stacking the two. Switchable off.
- **Best-lap highlighting can fill the cell instead of the text** — green
  or purple behind the lap time with the digits left white, for when the
  coloured text alone is too easy to miss. Coloured text stays the default.

### Relative

- **A car a lap apart now colours its gap as well as its name.** Only the
  name was tinted, so one half of the row said "this figure is not
  comparable to the others" while the other half read like any neighbour.
- **Every other row is shaded** here too, the same faint band as Standings
  and switchable the same way. It follows the row's place in the list
  rather than which cars happen to be showing, so the stripes stay put as
  drivers come and go around you.

### Delta

- **A row of sector boxes.** S1, S2 and S3 under the delta bar, each filled
  by how that split compared: yellow for no improvement, green for your own
  best, purple for the best in your class. The set holds for ten seconds
  after you cross the line, so you can read the lap you have just finished
  before it gives way to the one under way.
- LMU only. iRacing publishes no sector times at all, so the row is hidden
  there rather than shown permanently empty.

### Pedals

- **Speed and gear are now in the Pedals overlay**, in their own column to
  the left of the trace — gear, speed beneath it, KM/H beneath that — so
  you no longer need the Speed & Gear overlay alongside just for those two
  numbers. Switchable off, and the panel narrows back when it is.
- **The bars run clutch, brake, throttle**, left to right, matching where
  the pedals actually are.

### Visual

- **Manufacturer logos are sharp.** They were being resized twice —
  once to fit their box and once more when drawn — and landed on
  fractional positions, so every edge was smeared across two pixels. They
  are now rendered at the size they are actually displayed at, including
  when the overlay is scaled up.
- **PIT / OUT / GAR badges sit properly in their box.** The text was
  centred on the font's full height including the space reserved for
  descenders, which these all-caps badges never use, so the letters sat
  high.
- **The settings preview is sharp.** It is rendered at exactly the size
  it is shown at, but was then being smoothed on the way to the screen
  anyway.

### Calculators

- **A TIME column in both calculators**, beside LAPS: how long what is
  left in the tank will actually last, not just how many laps. Toggleable
  like every other column.
- Each row is priced at **its own** lap time — the LAST row against your
  last lap, the AVG 5 row against the average of the same five laps its
  usage figure comes from. So after one slow lap the two deliberately
  disagree, which is the useful part.
- Shown as a stint length rather than a stopwatch: "11:13" under an hour,
  "1h30" past it. With no lap time yet it shows "-" rather than a guess.

### Weather

- **The forecast row now shows how far through the session you are.**
  The fixed S / 25 / 50 / 75 / F labels are replaced by a bar that fills
  as the session runs, and each forecast icon now sits at the moment it
  actually predicts rather than in an evenly-spaced slot — so the bar
  genuinely reaches each one in turn. An icon dims once the session has
  passed it. A session with no set length leaves the bar empty rather
  than creeping along a made-up total.
- **Rain and wetness show which way they're moving.** A red arrow up or
  a green arrow down appears beside the value when it changes, and clears
  after five minutes without further movement.

### Smoothness

- **The overlays' stutter is fixed, and they now refresh about twice as
  often.** The render loop asked Windows for sixty updates a second and
  was quietly given thirty-two: Windows rounds a 16.7ms request up to its
  own ~15.6ms clock tick and fires on the second one. Overlays that
  redraw every other tick were therefore running nearer 16 times a second
  than 30. They now hold 30, and the Pedals overlay a real 60. This is
  what was being seen as the overlays briefly freezing.
- **The pedal trace no longer shows flat "plateaus".** Its points were
  timestamped when they were drawn rather than when the simulator
  produced them, so unevenly delivered frames recorded unevenly spaced
  points. It now plots against the simulator's own clock and records only
  genuinely new readings, so a repeated value is never drawn as a
  straight run.

### Fixes

- **The settings preview no longer freezes mid-animation.** It redraws
  only when you change a setting, so a change that moved rows around left
  the preview showing them part-way through the move until the next
  change. It does not animate at all now.
- **"Le Mans Ultimate" no longer runs under the game picker's arrow** —
  the name was wider than the space left for it. A name too long for the
  box is now shortened with an ellipsis instead of overlapping.
- **Standings' Interval was measured against the wrong car.** It used the
  previous row on screen rather than the car actually ahead, so with any
  row hidden or filtered the figure belonged to a different gap than the
  one being shown.
- **Cars with no finishing position sorted to the top instead of the
  bottom**, pushing the real leaders down the list. This is also why
  best-lap times could look like they had stopped appearing.
- **Class badges no longer clip their text** — wider abbreviations such
  as "BMW" ran to the very edge of the badge on both sides.
- **Fixed a crash when a car reported no tire compound.**
- **The settings preview box is larger**, so wider overlays no longer
  need constant scrolling to be seen, and overlay windows are kept within
  the monitor they open on.
- **HyperTrace could fail to start with nothing at all on screen.** Separate
  the .exe from the `assets` folder beside it — copy it out of the zip on
  its own, or launch it from inside the zip — and the app quit before
  drawing anything: no window, no message, nothing to report. The one file
  it genuinely cannot run without now travels inside the .exe, and anything
  else that stops it starting says so in a dialog instead of vanishing.
- **Errors are now written to a log file** at
  `%LOCALAPPDATA%\HyperTrace\errors.txt`, so a failure that used to leave
  no trace at all can be reported. It stays empty when nothing goes
  wrong.

---

## [1.2.3]

### Visual
- **Most overlay text now has a subtle drop shadow**, and so does the
  main window's (nav rail, buttons, labels, dropdowns) — it was reading
  flat ("2D") against varied backgrounds; a small bottom-right shadow
  gives it the readable depth other overlay apps use. Left out on text
  that sits directly on a bright, saturated fill (PIT/OUT/GAR/penalty/
  class badges, the whole Tyres widget, the Fuel/VE Calculator bars) —
  a dark shadow there just smeared instead of adding depth.

### Standings
- **Column order is now drag-and-drop** — grab a column and drop it where
  you want; the list slides open to show where it'll land. Replaces the
  old Up/Down buttons.

### New
- **A game picker in the main window's header** — groundwork for
  supporting more than one simulator. HyperTrace now tracks which one is
  actually running and will only show each widget's settings/columns
  that apply to it, hiding the rest outright rather than just greying
  them out. While no game is running, the picker lets you preview
  another simulator's settings ahead of time. LMU is still the only
  simulator actually supported end-to-end — this isn't a new one yet.

### Fixes
- **Tray icon's right-click menu no longer opens partly behind the
  taskbar** — "Show HyperTrace"/"Quit" were nearly unclickable since the
  menu expanded downward from the cursor, which sits right at the
  taskbar's edge. It now opens upward instead.
- **Closing the app (Close, not minimize) no longer leaves a dead tray
  icon behind** — the icon used to stay visible but stop responding to
  clicks for the whole shutdown sequence (overlays, bridge, up to a
  couple seconds), since the icon wasn't actually removed until the very
  end. It's now removed the instant you quit.

---

## [1.2.2]

### Standings

- **Gap and Interval no longer show a "+"** before the value — they're
  always "how far behind", so the sign was redundant.
- **Delta's colors flipped, and it no longer shows a sign** — a driver
  who was faster than you is now red, slower is now green (the reverse
  of 1.2.1), with direction shown by color alone.

---

## [1.2.1]

### Standings

- **New "Delta" column** — shows each driver's last lap compared to your
  own last lap: green when they were faster than you, red when slower.
  Shows decimals under 10 seconds, whole seconds above that. Reorderable
  and toggleable like every other column.
- **Column headers now use Title Case** ("Gap", "Best", "Delta", ...)
  instead of all-caps.

---

## [1.2.0]

### Rewritten as a native Windows app

HyperTrace is now a native C# (WPF) app with its own C++ telemetry engine,
replacing the previous Python/PySide6 implementation entirely — every
line of the desktop experience rebuilt from scratch, not just recompiled.
A single self-contained `HyperTrace.exe` — no separate Python install, no
dependency setup.

### Everything from 1.1.5's desktop experience carries over

- All 11 overlays, same look and behavior: Speed & Gear, Pedals, Tyres,
  Delta, Fuel Calculator, VE Calculator, Battery, Relative, Standings,
  Weather, Damage.
- **Presets** — save, load, rename, delete, save-as, and auto-apply a
  preset per driven class.
- **Lock/Free** and **Auto-hide**.
- **Drag-to-move** overlays, with magnetic snap to screen edges and to
  other overlays.
- **Standings' column order**, reorderable per your preference.
- **System tray** — minimize instead of closing, launch with Windows,
  a remembered choice for what × does the first time you close the app.
- **Single instance** — launching HyperTrace again just brings the
  already-running window to front instead of opening a second copy.

### New

- **Live visual preview in each overlay's settings dialog** — opening any
  overlay's settings (cog button) now shows that overlay rendered at its
  real size, right next to its controls, updating instantly as you change
  settings. Uses realistic sample data and works without LMU running.
- **Relative: lap-apart highlight can tint the row background instead of
  just the name** — new choice in its settings, for drivers a lap ahead
  or behind.
- **Battery: current lap / last lap turn red at ±10% consumption delta**
  — makes an unusually thirsty or efficient lap stand out at a glance.

### Removed / not available yet

- **Stream mode, Broadcast overlays, and the Live Timing panel** — present
  in 1.1.5, not yet carried over to the new app.
- **"Merge Fuel & VE calc"** option — dropped entirely rather than ported.

---

## [1.1.5]

### New: Settings tab
- **System tray icon** — HyperTrace can now stay running in the background instead of closing outright. A tray icon appears on launch with "Show HyperTrace" and "Quit".
- **Launch with Windows** — new toggle to start HyperTrace automatically when you log in.
- **Close button behavior** — the first time you close the main window, a dialog asks whether × should minimize to the tray or close the app completely; your answer is remembered and applied silently from then on. Changeable anytime from the new Settings tab (also home to Auto-hide, moved there from the Overlays page's Global controls).
- **Only one HyperTrace can run at a time** — launching it again while it's already running (including minimized to the tray) just brings the existing window to front instead of opening a redundant second copy.

### Fixes
- **Closing the app no longer hangs for a few seconds** — a few background threads (shared-memory connection, REST/WebSocket enrichment) were sleeping through fixed multi-second intervals instead of waking up immediately when told to stop, adding up to several seconds of delay before the app actually closed. Most noticeable with LMU not running.

---

## [1.1.4]

### Stream
- **Stream overlays now push instead of poll** — OBS Browser Sources receive new frames the instant they're ready (`multipart/x-mixed-replace`) instead of the browser re-requesting a PNG on its own as fast as it can, which also wastes work re-sending a frame that hasn't actually changed. Should mean lower latency and less CPU/bandwidth, especially on static or slow-updating overlays. The page URLs you already have saved in OBS are unaffected — nothing to reconfigure.
- **Replaced "Hide in garage" with the same visibility rule the desktop overlays use** — stream overlays now follow the global Auto-hide setting (Overlays page), hiding whenever you're not actively on track (covers pits, pause, menus — not just the garage) instead of only the narrow garage case.

### Fuel & VE Calculators
- **TANKS now shows 2 decimals instead of 1** — a 0.1-tank step is a big amount of fuel/energy, often several laps' worth, so it was too coarse to be useful.

### Fixes
- **Auto-hide OFF now actually always shows overlays** — it used to only cancel the "not actively driving" hide condition; a pause, alt-tab, or the main menu still hid every overlay (desktop and stream) regardless of the setting. Auto-hide OFF is now a full manual override — overlays stay up through all of that, showing the last known data — matching what the setting says it does.
- **Stream server no longer leaks its listening socket on restart** — toggling Stream/Broadcast off and on (or a port conflict auto-revert) now actually releases the port immediately instead of relying on eventual garbage collection.
- **Stream overlays render at the same sharpness as the desktop ones** — they were rendered at 1:1 regardless of screen scaling, one step behind the desktop overlays' resolution on any scaled display, most visible on detail-heavy ones like Damage (thin suspension lines, small corner arcs coming out visibly softer). Stream frames now render at the same scale.
- **Fixed a stream overlay getting stuck showing a blank/transparent frame after being hidden** — if a widget's content happened to be unchanged from before it was hidden (auto-hide kicking in, or the overlay's own stream toggle turned off and back on), it could stay stuck on the blank placeholder indefinitely once shown again, even though the desktop version recovered normally. Most noticeable on overlays whose content doesn't change often, like Damage.
- **Fixed a stream overlay sometimes displaying stale settings after a quick change** — e.g. changing opacity and immediately checking the result could show the previous value; the correct frame had actually already arrived (a page reload always revealed it), the browser just wasn't repainting it reliably. Frames are now drawn directly instead of relying on that.

---

## [1.1.3]

### Standings
- **New driver-count on the class badge** — shows how many drivers are in that class, as a helmet icon + number attached to the badge's flat right edge. Optional, on by default ("Driver count" in the widget's settings, under the class badge toggle).
- **New "Bottom drivers (your class)" option** — shows the tail-enders of your class in addition to the top drivers and the rows around your own position. Off by default (0).
- **New "Show DNF/DQ drivers" toggle** — hide retired/disqualified cars from every driver list and count (top/around/bottom, other classes). On by default (unchanged behavior); your own row is never hidden even if you retire.

### Relative
- **Fixed the red/blue lap-apart name tint showing outside the Race** — it was tinting names in Practice and Qualifying too, where being "a lap apart" isn't meaningful (different fuel loads, out-laps). Now Race-only.

### Fixes
- **Sharper small header/label text everywhere** — session info, column headers, and short captions like SOC/FUEL/LAST/BEST/AVG 5 could show faint gaps right where a letter's curve rounds (P, R, S…), most visible at the small sizes these use. Font hinting at that size was distorting the curve; that text now renders unhinted with a synthetic-bold pass to keep it looking as bold as before.
- **Standings/Relative's session clock no longer shifts as the digits change** — it now uses the same fixed-width digits as every other number in the app (Delta, Speed, lap times), instead of a proportional font where each new second could nudge the whole readout sideways.

---

## [1.1.2]

### Standings
- **New penalty tag** — a red tag showing each driver's outstanding penalty (drive-through, stop-and-go, or time), only visible when they actually have one. Sits flush against the far left or far right edge of the widget (your choice in the settings), outside the panel itself. Optional, on by default.

---

## [1.1.1]

### Relative
- **Driver names now tint red/blue when a car is a lap apart** — red if that car is about to lap you (or just did), blue if you're about to lap them (or just did). Optional, on by default ("Color name red/blue when a lap apart" in the widget's settings).

### Fixes
- **Fixed Standings' GAP and INTERVAL columns collapsing to "0.0" for the rest of the race once anyone in your class got lapped by the race leader** — a lapped car's own internal time reference breaks once that happens, and every other gap/interval in the class was quietly computed from it. Both columns are now computed independently of that reference and stay accurate all race, including once you or your class leader are a lap (or more) down.

---

## [1.1.0]

### New: Battery overlay
- **New "Battery" widget** — hybrid state-of-charge management. SoC bar (same gauge style as the Fuel/VE calculators, more compact — green in the normal range, orange under 20% or over 80%, red under 10% or over 90%), plus LAST LAP and THIS LAP net usage (negative while draining, positive while regenerating, resets crossing the line). This only means something on Hypercar — the widget doesn't hide itself for other classes, so turn it off by hand if you don't want to see it elsewhere.

### Damage overlay
- **Reworked car silhouette** — the wheels are now tucked flush against the bodywork instead of standing well clear of it, with the flanks broken open at each wheel arch, and the suspension arms moved in to match. Purely visual; the zones and what they show are unchanged.

### Fuel & VE Calculators
- **New "Reset AVG 5" setting** — the rolling 5-lap average can now auto-reset **Never** (default, unchanged), **At session start**, or **On pit exit**.
- **REFUEL, TO END and TANKS show the actual surplus instead of "OK"** — once you already have more than enough to finish, these now show exactly how much extra you're carrying (as a negative number) instead of just "OK".

### Relative
- **New "LAST LAP" column** — shows each driver's last lap time, including your own, in the same format as Standings, right before the Gap column. Green when it's that driver's personal best. Optional, on by default.
- **New brand logo column** — same manufacturer logos as Standings, between the position and the name. Optional, on by default.

### Tyres
- **The cold end of the temperature gradient is darker and starts later** — the fully-cold plateau now begins at -30°C below optimal (was -25°C) and is a visibly darker blue; the hot side (+25°C, full red) is unchanged.

### Fixes
- **Deleting the active preset now loads its replacement** — before, deleting the preset you were currently using switched the selection to another one but left every overlay in the deleted layout until you loaded it by hand.
- **Pausing no longer corrupts the next fuel/VE/battery reading** — any pause (alt-tab, replay, loading screen, not just a genuine session restart) used to throw away the running lap-consumption tracking and start it over from scratch, producing one bogus spike right after unpausing. Only a real new session now resets it.

---

## [1.0.0] — Renamed to HyperTrace

*(0.8.0 was never released publicly — its changes are folded in below, all counted against 0.7.2.)*

### Renamed: LMU App → HyperTrace
- The app is now called **HyperTrace**, with a new icon. Settings/logs moved from `~/.lmuapp/` to `~/.hypertrace/` — **nothing is carried over automatically**: you'll start with default overlay positions and **your presets need to be recreated**. Once you're set up, the old `~/.lmuapp` folder is no longer used and can be safely deleted.

### New: Damage overlay
- **New "Damage" widget** — top-down car silhouette , 17 zones total: 4 body edges + 4 corners, 4 wheels, 4 suspension wishbones, and the rear wing as its own zone. Each zone is coloured on a 4-level severity scale (grey/amber/orange/bright red for the most severe level).
- **Wheels** show detached/punctured state; **suspension** shows REST-only damage tiers; **body zones and the rear wing** are shared memory. No text or numeric readout — the silhouette is the whole display, matching the design spec.
- Suspension damage is REST-only — LMU has no shared-memory equivalent for it.

### Main window redesign
- **Sidebar layout** — the window is now a wider (560px) panel with a navigation rail on the left (Overlays / Presets / Stream / Broadcast, active page marked with an amber bar) instead of the old top tabs, in the style of typical sim-racing companion apps.
- **Header bar** — app name and version always visible at the top, on every page.
- **Status footer** — a permanent strip at the bottom shows at a glance whether the game is connected, REST enrichment is active, the stream is on, and broadcast is on.
- **Global controls grouped** — Lock/Free, Auto-hide and Merge Fuel & VE now live in a visually distinct "Global controls" card at the top of the Overlays page.
- **One single preset control** — a dropdown to switch, plus Save / Save As, at the bottom of the Overlays page; the active preset is also highlighted in the Presets page list.
- **Deleting a preset now asks for confirmation** — the trash button turns into a check on first click; clicking the check confirms the deletion, and it reverts to a trash on its own after a couple of seconds if you don't. No popup dialog.
- **Fixed Broadcast settings resetting on every launch** — the app was force-resetting that toggle to on at startup regardless of what was saved; it now stays exactly as you left it.
- **Tower is now off by default** on a fresh install, matching Battle/Driver Card/Sectors (it used to be the only one of the four turned on automatically).
- **Each preset is now its own file**, under a new `presets/` folder next to the config, instead of all being bundled together inside the main config file — easier to back up, share, or edit a single preset by hand.
- Internal: the window's small custom controls moved to their own module (`main_window_controls.py`), the hand-rolled segmented buttons and the triple-duplicated Battle/Driver Card/Sectors exclusivity were replaced by two small reusable components, and the toggle colors moved into the central theme.

### Fuel & VE Calculators
- **Fixed REFUEL showing absurd values** (a long race with a low-consumption class could show a refuel amount many times over 100%). REFUEL now shows what actually makes sense to add at your *next* stop, capped to what the tank can hold; the old "FINISH" column is now **"TO END"** and shows the *total* amount still needed for the rest of the race, uncapped — which is what could grow that large, just correctly labeled now.
- **New "TANKS" column** — number of full tanks/refills still needed to reach the end of the race, e.g. 400L needed with a 50L tank reads "8.0". Shown alongside "TO END".
- **REFUEL and TO END now also work in Practice and Qualifying**, not just Race.
- **More accurate numbers overall** — LAST and AVG 5 now read each lap's consumption from the same background engine that already ran everything else in the app, instead of a simpler estimate computed inside the widget itself. Laps remaining now accounts for exactly where you are on the current lap rather than rounding to the nearest whole lap.
- **Fixed the VE bar always showing green regardless of level** — it now turns orange under 25% and red under 10%, matching the VE column in Standings.

### New: Auto-hide (replaces "Hide in garage")
- New **Auto-hide** toggle in Global Controls (Overlays page) — when on, every overlay hides automatically unless you're actively driving on track, same as the game's own on-track detection. Off by default.
- **Replaces the old "Hide in garage" toggle**, which is now removed for desktop overlays — Auto-hide already covers the garage case and more (menus, replays, anywhere you're not actually driving). The Stream page keeps its own separate "Hide in garage" toggle, unaffected.

### Class badges
- **LMP2 and LMP3 now show their full names** instead of "P2"/"P3" wherever a class badge appears.

### Under the hood
- **One typeface across the whole app** — the Live Timing panel was still drawn in the system font, and its session clock in a third font again, while everything else used Montserrat; all of it now matches. The unused JetBrains Mono and Saira SemiCondensed files are no longer bundled either, which takes about a megabyte off the download.
- **REST enrichment no longer runs when there's nothing to enrich** — the background thread that queries LMU's local API (car numbers, team names, class gaps, weather forecast, suspension damage) used to send requests five times a second even with the game closed, on a loading screen or alt-tabbed. It now waits until a session is actually live.
- **Third-party attribution** — the app now ships a `THIRD_PARTY_NOTICES.md` crediting the GPLv3 project the calc engine and the overlay update loop are adapted from.

---

## [0.7.2]

### Widget settings
- **Per-session visibility** — every overlay's settings now have a "Visibility in session" section with Practice/Qualifying/Race toggles, so an overlay can be hidden during specific session types.
- **New "Apply to preset" button** — opens a checklist of every saved preset; tick any number of them and confirm once to write that overlay's current position and settings directly into all of them, without loading each one (and overwriting everything else in it) first.
- "Column order" entries (Standings) are now bold, matching the weight of the rest of the settings labels.

### Standings
- **VE/Fuel column is now shown by default.**
- **Fuel level for other cars now shows "-" instead of a value** — it isn't broadcast for other cars in online races, only the player's own is ever accurate. Virtual Energy is unaffected and still shown for everyone.

### Speed & Gear
- Fixed the speed digits shifting slightly as the value changes — same tabular-figures fix already used for lap times and gaps elsewhere.

### Main window
- "Hide overlays in garage" is now a pill toggle (matching the lock/free one) instead of a checkbox, labeled "Overlays visible/hidden in garage".
- Removed the description text above the preset list in the Presets tab.

### Broadcast
- **New master "Broadcast" on/off switch**, at the top of the Broadcast tab — lets you manually stop/restart REST (localhost:6397) without closing the app. REST still starts automatically on launch, unchanged.

---

## [0.7.1]

### Overlay visibility
- **Fixed overlays staying visible after being kicked back to the main menu** (e.g. a practice session with no qualifying/race after it), without hiding them early while still on track when a practice session's timer simply reaches zero. Visibility now checks whether the session clock is still actually advancing, instead of a session-phase flag that also flips the moment the timer runs out while still driving.

### Standings & Relative
- **Fixed remote opponents showing a PIT badge in multiplayer while clearly on track.** Per-car telemetry isn't reliably synced for remote vehicles over the network; the pit-lane detection for other cars now relies on a single, more reliable field instead of also factoring in telemetry data. The player's own pit-lane detection is unchanged.

---

## [0.7.0] — Data & rendering engine rewrite

### Engine
- **The telemetry/calculation engine has been rebuilt on a more robust, modular architecture.** Data reading, session detection, delta/fuel/VE calculations, standings/relative gaps, and the overlay update/visibility engine now run on proven patterns instead of this app's own earlier hand-rolled logic (see `THIRD_PARTY_NOTICES.md` for the open-source reference this was adapted from). The visual design, layout, colors, fonts and all settings of every overlay are unchanged — only what's underneath changed.
- Fixes several long-standing sources of fragility this way: session-reset detection (used to reset fuel/VE history, outlap/pit badges) is now based on a robust signal instead of a heuristic; the local player's telemetry is now matched by car ID instead of trusting a raw index, which is more reliable when the game reorders internal arrays; on-track detection now reflects actually driving (ignition/realtime state) rather than just "a session is running".
- Per-car sector times (used for gap columns) now come directly from shared memory instead of a slower REST poll — one less thing relying on the REST API to work.

This is a foundational change — please report anything that looks off, especially around session transitions (practice → qualify → race, or restarting a session).

### Presets
- **Presets are now created and saved from the Overlays tab.** A "Preset" row shows the currently loaded preset, with a **Save** button to overwrite it and a **Save As…** button that swaps the row for a name field to create a new one.
- **Removed the "Auto-load on session change" checkbox and the Practice/Qualifying/Race dropdown assignments.** Replaced with a **"Preset per class"** panel in the Presets tab — one dropdown per car class (Hypercar, LMP2, LMP3, GT3, GTE) to pick its dedicated preset, which then loads automatically as soon as you're driving a car of that class.

### Class colors
- **Removed the Colors tab.** Vehicle class colors (Hypercar, LMP2, LMP3, GT3, GTE) are no longer user-configurable and always use the app's defaults.

### Main window
- The control panel window can no longer be resized taller/shorter by dragging its edge — its height now follows each tab's own content instead.

### Widget settings dialogs
- **Fixed the Copy / Paste / Reset buttons clipping their text** on every overlay except Standings (whose settings dialog is wider due to its side panel). Shortened to "Copy" / "Paste" / "Reset".

### Delta
- The Last/Best lap time values and the live delta value are now smaller and closer in size to each other, instead of the delta being noticeably larger than the times.

### Speed & Gear
- **RPM bar shift light** — the bar now reads full at 92% of max RPM instead of 100%, and blinks blue every 100 ms from 95% onward as a shift cue.

### Weather
- The wetness row is now labeled "WETNESS" instead of the more ambiguous "WET".

---

## [0.6.13] — Performance & CPU usage

### Game freezing / CPU usage
- **Fixed the app causing the game to freeze while overlays were visible.** Each overlay is a separate always-on-top, per-pixel-alpha window; Windows has to recomposite all of them on every repaint, which competed with the game for the same CPU cores under load — consistent with the freezes only happening while overlays were shown, never while idle. The app's process priority is now set to Below Normal on startup, so Windows favors the game whenever both want the same core.
- **Fixed the Pedals overlay running two independent 60 fps repaint timers at once** instead of one — halves its timer overhead for the same smooth trace scrolling.
- Lowered the refresh rate of Weather, Standings, Fuel Calculator and VE Calculator to 1 fps — none of them show fast-changing values, so the higher rate was pure overhead.
- Lowered the Pedals overlay's own refresh rate from 60 fps to 30 fps.

### Fuel & VE calculators
- **Fixed the Fuel Calculator rendering a few pixels narrower than the VE Calculator.** Both size their table columns from a reference value string, and `%` (VE) renders wider than `L` (Fuel) at the same size; Fuel Calculator now sizes off the same reference so the two always match.

### Tyres
- **Hard tyre badge now uses the exact same red as the Hypercar class badge**, instead of a separate red that was close but not identical.

---

## [0.6.12] — Documentation

### README
- Fully rewritten — it still only described 6 of the 9 overlays and a source-only install. Now covers every current overlay, the packaged `.exe` as the primary way to run the app, stream mode, controls (snap, lock, presets, hide-in-garage), and where config/logs live.
- Corrected the in-game requirement: **Settings → Gameplay → Enable Plugins**.

---

## [0.6.11] — Montserrat font, layout fixes & coherence pass

### Overlay defaults
- **Fixed the VE Calculator being disabled by default on a fresh install** — every other overlay defaulted to enabled, this one alone was hard-coded off in the config defaults.

### Overlay sizing
- **Fixed overlays shrinking the instant any setting was first touched, and rendering oversized before that.** The code's own default scale (115%) disagreed with every widget's own settings-schema default (100%): a fresh install rendered at 115%, then the settings dialog would apply the schema's 100% the first time any control was touched. The code default is now 100%, matching every schema (Delta's own default scale also moved from 80% to 100%, per the same "always 100%" rule).
- **Recalibrated base sizes now that 100% is honest.** Tyres, Speed, Weather, and the Fuel/VE calculators used to be inflated by the 115% bug without anyone deciding it that way; their own pixel dimensions are increased so 100% still looks like what those widgets have always looked like. Delta — deliberately doubled earlier — is brought back down to exactly double its *original* size now that there's no extra 80%→100% scale change compounding on top of it.

### Overlay positioning
- **Fixed magnetic snap triggering across the whole screen.** X and Y snapping were evaluated independently, so a peer overlay whose edge happened to line up would snap even hundreds of pixels away on the other axis. Snapping to a peer's edge on one axis now requires that peer to actually be nearby on the other axis; ordinary stacking/side-by-side snapping with a normal gap is unaffected.

### Lap time colors
- **Fixed the last-lap color (purple/green) never showing on a new personal or session best**, in Standings, Delta and Live Timing. `best_lap` is the minimum lap time *including* the last one, so the instant a lap sets a new best, `last_lap` and `best_lap` become equal — the strict `<` comparison could (almost) never be true at exactly the moment it should fire. Changed to `<=` for this specific "did my last lap equal my best" check (unrelated to the other strict comparisons, which compare a live time against a separate, unmoving reference).

### Standings
- Column header labels (`GAP`/`INT`/`BEST`/`LAST`) reduced by two sizes — they matched the driver-name size, which read as too large (a one-size reduction wasn't a big enough step to notice).

### Relative
- Added a small gap between the position chip and the driver name.
- Added a small gap between the name/badge zone and the relative-time value, so a wide value like `+123.4` no longer touches a `PIT`/`OUT`/`GAR`/`L`*n* badge — the column width reference was based on a 2-digit gap (`+12.x`), too narrow for the 3-digit gaps a long track like Le Mans can produce; it now matches Standings' `+999` reference.

### Speed & Gear
- **Fixed the still-oversized gap between `KM/H` and the gear.** The widget's width was computed from a content-area height formula that didn't match the one `paintEvent` actually used (40 px assumed vs 26 px real), sizing the layout for text far larger than what gets drawn and leaving a large unexplained gap. Both now share one formula.
- **Fixed the gear digit being clipped on the left.** The gear column was sized to fit `"8"`, but `"N"` (neutral — shown any time you're stopped) and `"R"` are both wider; Qt clips `drawText` to its bounding rect by default, so the left edge of those glyphs was silently cut off. The reference now covers every character the gear display can show.

### Fonts / bold text
- **Class badge (standings) and status badges (`GAR`/`PIT`/`OUT`/`L`*n*, standings and relative) now render with the same synthetic-bold weight as the rest of the text.** Requesting a heavier `QFont.Weight` has no effect since only one Montserrat weight is bundled; at these small sizes the single embedded weight reads as visibly thinner than larger text.

### Delta
- The "no lap yet" placeholder is a `-` (hyphen) instead of an em-dash, which rendered as a disproportionately large solid bar (35 px wide vs 10 px) next to the lap-time digits.

### Fuel & VE calculators
- The `VE`/`FUEL` bar and level labels were noticeably smaller than the value next to them; bumped from an 8 px to an 11 px render size.

### Shared memory
- **Fixed the app never receiving data when started before LMU.** `mmap` with a tag name *creates* the mapping when it is missing, so the app attached to its own empty mapping, reported a successful connection and read zeros forever. The mapping's existence is now probed first, and a mapping that only ever reads zeros is dropped and reconnected. Launch order no longer matters.
- Failures now report the Windows error code, distinguishing "LMU is not publishing" from "access denied" (elevation mismatch).
- Added a rotating log file in `~/.lmuapp/lmuapp.log`: the packaged app has no console, so nothing was diagnosable on a machine without Python. Each overlay also logs why it is shown or hidden.

### Standings
- **Status badges (PIT / GAR / OUT / L*n*) now have their own column** instead of being drawn over the end of the name column, where they truncated long names. It can be reordered like any other column.
- Badge width is derived from the actual text metrics, so labels keep an even margin at every font size instead of touching both edges.
- **Manufacturer logos are sharp again** — they were rasterised at 3× and shrunk by the painter, whose bilinear filtering softens a >2× downscale. Vector logos are now rasterised directly at their on-screen size.

### Text rendering
- **Letter tracking removed everywhere.** The 14% tracking applied to labels visibly spaced out short codes (`GT3`, `GAR`) and pushed centred single glyphs off-centre.
- The synthetic-bold workaround introduced in 0.6.9 is now limited to text containing digits. Applying it to driver names and labels made them look blurry, since it works by drawing the text twice with a sub-pixel offset.

### Relative
- The header shows only the **remaining** session time; the previous "elapsed / total" form was twice as wide and got clipped with a narrow name column.

### Typography
- **Montserrat Bold is now the app font**, for text and numbers alike. The OpenType `tnum` feature is enabled on numeric text so every digit keeps the same advance — lap times, gaps and the live delta stay aligned instead of shifting on each update. JetBrains Mono remains as a fallback.
- **Font sizes are now expressed in pixels** rather than points. A point size is converted using the screen DPI and then rounded, so consecutive settings steps could render identically; pixel sizes always differ. Overlays also render identically on machines with different DPI or Windows scaling.
- Fixed the smallest font sizes rendering identically: a floor in the derived sizes made steps 7 and 8 produce exactly the same text.

### Standings & Relative
- Default font size raised to **11**; default name width lowered to **150 px**.
- **Header height now follows the font size** — it was a hard-coded constant, so it never adapted.
- **Column header labels are now the same size as driver names** (same perceived weight), instead of a smaller derived size.
- The name column is configured in **pixels** with a slider instead of a character count, which no longer maps to a width with a proportional font. Names are elided to the real column width instead of being cut at N characters.
- **Standings**: fixed pit/out-lap badges never resetting on a session change or restart — the same fix applied to Relative in 0.6.9 had been missed here, so a stale `OUT` / `PIT` / `L*n*` badge could survive into the next session.
- **Relative**: the gap/interval column width is now measured from real font metrics instead of a per-character estimate, which could run 2 px too narrow at large font sizes and clip the value.
- Fixed a stale fallback color (`#ffc800`) used only when a saved config predates the `player_color` setting; it no longer disagrees with the setting's own default (`#ECAA43`).
- A `-` dash is always white (`T.TEXT`), never dim (`T.DIM`) — fixed one remaining case in the Standings VE/Fuel column, and unified it from `---` to a single `-` like every other empty value.

### Tyres
- Removed the compound-badge letter (S/M/H/W) — unreadable at this size; the badge colour alone already identifies the compound.

### Delta
- Widget doubled in size (200×… instead of 100×…), fonts scaled to match.

### Speed & Gear
- Fixed **`KM/H` overlapping the gear** — the widget width was a hard-coded constant that assumed the previous monospaced font; Montserrat's wider digits made the speed block alone exceed it. Width is now computed from the fonts actually in use.

### Pedals
- Fixed the trailing `0` being clipped on `100`: the value box was 1 px narrower than the text it had to hold.

### Removed
- `DEFAULT_COLUMNS` (Standings): a stale, unused module constant listing an outdated set of default columns.

---

## [0.6.10] — App icon & display fixes

### App icon
- The application logo is now used for the **window title bar** and the **taskbar**.
- Windows: an explicit AppUserModelID is set so the app no longer inherits the Python icon and gets its own taskbar entry when run from source.
- A `.ico` is generated from the logo and embedded in the executable, giving `LMUApp.exe` its own icon in Explorer and when pinned.

### Fuel & VE calculators
- Units are no longer separated from the value: `58.0%` and `58.0L` instead of `58.0 %` / `58.0 L`.
- Since columns are sized to their content, the widget is **19 px narrower** as a result (233 → 214 px).

### Weather
- Fixed the **flattened `0`** on temperatures, RAIN/WET percentages and the forecast node labels — same hinting artefact already fixed elsewhere in 0.6.9.

### Settings
- **Column order (Standings)**: fixed rows painting on top of each other when toggling a column or reordering. Rows removed from the layout stayed children of the container and kept being drawn until the next event-loop pass.

---

## [0.6.9] — Performance, text rendering & pit detection

### Performance
- **Stream mode no longer stutters the on-screen overlays** — PNG encoding moved off the Qt GUI thread onto a dedicated encoder thread with a latest-wins queue. The GUI thread now only rasterises the widget; the zlib compression runs on another core.
- **Reader split into two cadences** — the heavy full-field scan (all vehicles, REST merge, telemetry loop) is throttled to ~10 Hz while player telemetry stays at full rate, cutting allocations and GC churn by ~5×. Standings/relative already sampled at 5-10 Hz, so there is no visible difference.
- Full-field rescan forced immediately on session change or when the car count changes, so the field is never stale.
- Reader micro-optimisations: memoized string decoding (driver/team/class/model names were decoded for every car on every tick), compound-type map hoisted to a module constant, `import math` moved out of the hot path.
- **Pedals overlay** — dedicated 60 fps render timer and wall-clock trace scrolling, decoupled from the 50 Hz data feed (removes the 60/50 Hz beat stutter).

### Text rendering
- Fixed the **flattened `0`** and the **asymmetric capital `M`** at small sizes: font hinting snapped round glyphs to the pixel grid. Hinting is now disabled on the affected text, with synthetic bold (`draw_bold`) restoring the weight that hinting used to provide.
- Applied to session headers (relative, standings), tyre temperatures and wear %, the compound badge letter, the `KM/H` unit and driver names in standings, relative and broadcast.
- Compound badge letter is now correctly centred — the label letter-spacing added a trailing gap that pushed a lone glyph off-centre.

### Pit detection
- **PIT badge now appears after leaving the garage.** No single field covers every case: `mPitState` only tracks a pit *stop* sequence, and `mInPits` stays false when driving out of the box. `in_pit_lane` now combines `mCurrentSector`'s pit-lane sign bit, `mPitState >= 2` and `mInPits`.
- Handles the undocumented `mPitState = 5` observed when leaving the garage (the header only documents 0-4).
- Pit state is centralised in the reader instead of being re-derived in each widget, and is used by standings, relative, broadcast and live timing.
- **Relative**: `GAR` badge added for the player — other drivers in the garage are filtered out of the list, so the case was never handled and showed `PIT` instead.

### Session handling
- New `session_id`, bumped on session change **or restart**, giving widgets a reliable per-session reset signal. Fuel calculator, VE calculator and relative badges now use it instead of the fragile "lap counter went backwards" heuristic.

### Tyres
- Tyre colours are now derived from each tyre's **own optimal temperature** (`mOptimalTemp`, read per wheel) instead of fixed thresholds, so they adapt per car and per compound.
- The four temperature-range settings (Cold below / Optimal from / Optimal to / Hot above) have been removed — they no longer have any meaning.

### Weather
- The forecast is now fetched by the reader; **the weather widget no longer performs any REST call**.
- Current sky type is read from shared memory (`mCloudCoverage`) and shown immediately while the forecast loads, instead of "NO DATA".
- Forecast fetched at launch and refreshed on every session change.

### Manufacturer logos
- **Logos were never displayed** — the loader pointed at a non-existent folder, searched for `.png` while the files are `.svg`, and used a matching rule that could never succeed.
- SVGs are now rendered at the target size via `QSvgRenderer` (sharp at any scale) rather than rasterised at source size and downscaled.
- PNG sources are supported too: the Porsche "SVG" was a raster image wrapped in an SVG (`pattern` + embedded base64), which Qt's SVG 1.2 Tiny renderer cannot draw.

### Fuel & VE calculators
- Table columns are now sized to their content instead of being split equally — `REFUEL` was truncated (`+99.9 %` needs 52 px but only had 35).
- Values keep one decimal up to 99.9 and drop it at 100 (`100 %` / `100 L`, never `100.0 %`).
- Missing values display a single `-`.

### Removed
- Offline/mock mode fully removed: `MockReader`, the `mock` parameter of `DataReader`, the `tests/` directory and the pytest configuration.

---

## [0.6.8] — Broadcast polish & lap time color fixes

### Broadcast Tower
- **P1 row** now shows best lap time (practice/quali) or "LEADER" (race) in the GAP and Interval columns
- Column header labels now align correctly with the data column (was offset by the logo column width)
- POS +/- column is now per-class in Overall mode (was overall position delta)
- Column headers renamed: "Interval" (was "INT"), "Pos +/-" (was "POS")

### Broadcast Battle
- Gap display is now refreshed every 2 s to avoid visual noise
- Rival filter now tolerates ±1 lap difference (prevents card disappearing when crossing the finish line)

### Broadcast Driver Card
- Last lap time is now colored purple/green when improved, white otherwise (was always white)

### Broadcast Sectors
- Sector bars thickened to 26 px; sector time displayed inside the bar
- After crossing the finish line, sector data stays visible for 10 s then goes blank

### Lap time color convention — all overlays
- **Strict `<` comparison everywhere** — equal times are no longer considered an improvement (no more `+0.001` / `+0.002` tolerance)
- Rule: `last < personal_best` → green; if also `personal_best ≤ class_session_best` → purple
- Same logic applied to sectors: `t < personal_sector_best` → green; `t < class_sector_best` → purple
- Applied across `broadcast.py`, `live_timing.py`, `standings.py`, `delta.py`
- No improvement → yellow in broadcast overlays and live timing; white in standings and delta

### Refresh rate
- All broadcast overlays reduced to 20 Hz (was higher)

---

## [0.6.7] — Compound badges & sector color fixes

### Broadcast overlays — compound badges
- **Driver Card, Battle, Sectors**: tire compound badge added to each widget
  - 4 identical compounds → large circle with letter (S / M / H / W) on colored background (red / yellow / grey / blue)
  - Mixed compounds → 4 small colored dots (no letter), same footprint as the circle
- Compound data sourced from `mWheels[i].mCompoundIndex` (shared memory, all vehicles) cross-referenced with the TireManagement REST endpoint polled every 30 s for the authoritative index→name mapping
- **Driver Card, Battle, Sectors are mutually exclusive** — enabling one automatically disables the other two

### Sector color convention (Broadcast Sectors)
- **Purple**: session best in class (≤ leader's reference time)
- **Green**: personal improvement (≤ own personal best)
- **Yellow**: worse than personal best
- Previously, green was shown when faster than the previous lap (not vs personal best) and all three bars turned yellow on lap completion

### Live-timing standings
- Sector color fix also applied to the "last lap" column: purple = session best, green = personal best, white otherwise

---

## [0.6.6] — Overlay UX & settings polish

### Overlay positioning
- **Snap to screen edges** — overlays magnetically snap to screen edges when dragged within 5 px
- **Snap to other overlays** — overlays also snap to each other's edges and sides for easy alignment
- **Keyboard nudge** — hold left mouse button on an overlay then use arrow keys to nudge 1 px at a time; Ctrl+arrow moves 10 px

### Settings dialog
- **Reset to defaults** button — restores all settings for a widget to their default values in one click
- **Standings**: reorganised sections — font size moved to Appearance; cleaner labels; "Player row" and "Badges" sections; columns listed in logical order with decimals immediately below their toggle
- **Relative**: restructured — Appearance (opacity/scale/font size), Rows (drivers + gap decimals), Names, Player row, Header (content hidden when header is off), Badges
- **Fixed**: horizontal scrollbar no longer appears in the Standings config dialog
- **Fixed**: dialogs without a side panel are now constrained to 400 px width; scrollbar no longer collides with content

### Fonts
- **JetBrains Mono zero** — the zero digit is now a plain oval (no slash, no dot), eliminating confusion with 8

---

## [0.6.5] — Manufacturer logos in broadcast overlays

### Broadcast Tower
- **Manufacturer logo column** — a logo column between position and car number displays the manufacturer brand logo, sourced from `assets/brandlogo/`; matched from the vehicle model name (`mVehicleModel` from telemetry data)

### Broadcast Driver Card
- **Manufacturer logo** — logo displayed between position number and car number on the main row

### Broadcast Battle
- **Manufacturer logo** — small logo shown below the car number in each driver's position column

---

## [0.6.4] — Delta overlay & bug fixes

### New: Delta overlay
- **Last Lap / Best Lap / Delta** — compact overlay showing last lap (color-coded: purple = class best, green = personal best, white = no improvement), personal best lap in purple, and live delta vs best lap
- **Delta bar** — centered bar visualising the gap (green left = gaining, red right = losing); range configurable in settings
- Available in stream mode

### Bug fixes
- **Parade crash** — broadcast tower no longer crashes when all drivers DNF or enter garage while parade mode is active
- **QBuffer leak** — stream PNG buffers are now explicitly closed after each render (was leaking at 30 Hz)
- **REST race condition** — `_rest_focus` and `_rest_data` now protected by a dedicated lock; reads take a snapshot to minimise lock hold time
- **REST thread not joined** — `LMUReader.stop()` now joins the REST thread before returning
- **Bounds check on `playerVehicleIdx`** — guards against out-of-range telemetry index (0–103)
- **Session reset** — fuel/VE history and pit/outlap badges now clear correctly when a new session starts

---

## [0.6.3] — Live Timing & Pedals

### Live Timing
- **Sector times** — S1 / S2 / S3 columns added; shows current in-progress sectors when available, falls back to last lap; color-coded per class (purple = class best, green = personal best, yellow = no improvement)
- **Session label** — displays full name (PRACTICE / QUALIFYING / RACE) instead of abbreviated code
- **Header order** — session name first, then remaining time, then track name

### Pedals (stream)
- **Per-pedal toggles** — throttle, brake and clutch can each be enabled or disabled independently; widget resizes automatically
- **Per-channel trace toggles** — each trace curve (T / B / C) can be shown or hidden independently
- **Stream refresh rate** — configurable per widget via `stream_hz`; tick loop runs at 60 fps with per-widget throttling

---

## [0.6.2] — Visual polish

### All overlays
- **JetBrains Mono everywhere** — F_TEXT and F_NUM unified, Bold by default, TypeWriter style hint to ensure correct font resolution
- **Dashes "-"** are always white in all columns (best, last, gap, interval)

### Standings
- **Per-class best lap** — purple only for the best time within a driver's own class (multiclass fix: HYP and GT3 each have their own reference)
- **VE/Fuel color coding** — green ≥ 20% / 20 L, orange < 20, red < 10
- **Position column** widened to fit 2-digit numbers
- **Header font** separated from class badge font — column labels at 7.5 pt, badges unchanged

### Tyres
- **Uniform spacing** — outer margins and inter-tyre gaps are identical (`_G = 4 px`)

### Relative
- **Interval column** — width adjusts dynamically based on the configured decimal count

### UI
- Live Timing no longer opens automatically on startup

---

## [0.6.1] — Overlay size & camera polish

### All overlays
- **Default size +15 %** — all overlays are 15 % larger out of the box; configurable via a single `DEFAULT_SCALE` constant in `base.py`

### Live Timing
- Camera switching to WS / CP is now significantly faster — advances the Onboard ring in one calculated step instead of polling in a loop
- CP camera fixed: corrects off-by-one errors with a single verification pass after switching

---

## [0.6.0] — Broadcast mode & Live Timing

### New: Broadcast tab
- New **Broadcast** tab in the main window, dedicated to director / broadcast tooling
- **Tower** overlay — live standings rendered as a broadcast tower; three modes: *Overall* (top N), *Multiclass* (top N per class), *Class* (top N of one class)
- **Battle** overlay — highlights the two drivers currently fighting for position
- **Driver Card** overlay — shows the currently viewed driver's name, position and gap
- Toggle between **Driver Name** and **Team Name** display across all broadcast overlays (full name shown, never truncated)
- Tower, Battle and Driver Card can each be enabled or disabled independently
- A single **/broadcast** browser-source URL combines all three overlays into one OBS source — copy it directly from the tab

### New: Live Timing Panel
- Standalone window opened from the Broadcast tab via **Open Live Timing Panel**
- Full live timing table: position, class color chip, car number, driver / team name, class, best lap, last lap, gap to leader and status
- **TV / WS / CP camera buttons** on every driver row — click to focus that driver *and* switch camera simultaneously:
  - **TV** — TracksideCycle (broadcast trackside cameras)
  - **WS** — Windshield onboard
  - **CP** — Cockpit onboard

### Stream
- **Hide in garage** checkbox — overlays go transparent while the player is in the garage; re-appear automatically on track

---

## [0.5.1] — Stream improvements

### Stream
- **OBS clears on exit** — a transparent frame is pushed to all overlays before the server stops, so OBS shows nothing instead of a frozen image
- **Hide in garage** — new checkbox in the Stream tab; when checked, stream overlays go transparent while the player is in the garage
- Stream tab moved after Presets in the tab bar

---

## [0.5.0] — Stream mode & Weather overlay

### New: Stream mode
- **Stream tab** — new tab in the main window to configure OBS integration
- Local HTTP server (configurable port) serves each overlay as a browser source URL
- Each overlay can be enabled/disabled independently for stream, with its own settings (opacity, scale, etc.)
- **Copy URL** button per overlay to paste directly into OBS Browser Source

### New: Weather overlay
- Air temperature, track temperature, rain %, path wetness
- Session forecast with sky condition icons (clear → storm) polled from LMU's REST API

### Settings dialogs
- **Copy / Paste Settings** — copy settings from any overlay's config dialog and paste into another (e.g. normal → stream or vice versa)

### Standings & Relative
- Air / track temperature display is now left-aligned in the session bar

### Relative
- "Nothing" header option now fully hides the session bar instead of leaving it empty

---

## [0.4.2] — Visual fixes

### All overlays
- **Opacity now affects the accent hairline** — the yellow gradient at the top of each overlay fades with the opacity setting
- **Settings `show_if`** — dependent rows are now hidden entirely instead of grayed out

---

## [0.4.1] — Standings & Relative polish

### Standings
- **Lapped cars** — gap column shows `+1L`, `+2L`, etc. instead of a gap in seconds; uses `time_into_lap` to avoid false positives when the leader just crossed the finish line
- **Pit lap badge** — `L{n}` badge now has a yellow background and black text, fully opaque
- **Dynamic column widths** — GAP/INT columns sized for `+999.X`, BEST/LAST for `9:99.XXX`, computed from actual font metrics at the configured decimal precision
- **Uniform column spacing** — constant `_CP = 3 px` padding on each side of every column for consistent visual gaps
- **Header info** — single dropdown replaces three separate booleans; shows session letter + elapsed/total time side by side (e.g. `R  1:00:12 / 4:00:00`)

### Relative
- **Header info** — same dropdown as Standings; shows full session name + time (e.g. `RACE  1:00:12 / 4:00:00`)

---

## [0.4.0] — UI polish

### Main window
- **Presets** — save the current position and settings of all overlays as a named preset, load or overwrite it at any time
- Main window no longer stays on top of other apps

### Settings dialogs
- Visual style now matches the main window
- Standings settings use a two-column layout (less scrolling)

### Standings & Relative
- New name casing option: ALL CAPS / Name LASTNAME / Name Lastname

---

## [0.3.2] — Polish & bug fixes

### Speed
- Overlay is more compact
- RPM bar now spans the full width of the overlay
- The "KM/H" label repositions automatically depending on how many digits the speed has (e.g. "9" vs "300")

### Inputs
- Overlay is more compact
- Spacing between pedals, steering wheel and edges is now equal on both sides
- Throttle / brake / clutch bars are drawn as solid colors (lighter to render)

### Tyres
- Tyre name (FL / FR / RL / RR) is now centered inside its rectangle
- Temperature is displayed at the top center, above the tyre name

### Standings
- Position number is centered in its column
- PIT / GAR / OUT badge is now correctly aligned to the right edge of the name column
- Player's class header (e.g. "HYP HYPERCAR") stays visible even when "Show other classes" is turned off
- Long driver names (e.g. PIER GUIDI) no longer overflow onto the badge

### Relative
- Gap intervals are displayed in plain white — no more color distinction between drivers ahead and behind
- Player name is displayed in white like all other drivers (no more yellow highlight)

### Fuel Calculator / VE Calculator — Merge mode
- Rule is now clearly: **Hypercar or GT3 → VE Calc**; all other classes → Fuel Calc
- All `---` dashes are displayed in white (some were previously shown in grey)

### Main window
- ON / OFF buttons now have a solid, fully opaque background: bright green for ON, bright red for OFF
- Checkboxes now display a white tick when checked

### Fixed
- Fuel / VE overlay flickering when toggling Merge mode — fixed
- Fuel / VE overlay flickering in the garage while Merge mode was active — fixed
- VE Calculator not showing in Hypercar in some cases — fixed
- General rendering performance improvements (fewer calculations per frame)

---

## [0.3.1]

### Fixed
- **Fuel & VE Calculator** — The FINISH column now shows a value only when current fuel / VE is sufficient to finish the race; displays `---` if a pit stop is required

---

## [0.3.0] — Broadcast visual redesign

### New
- All overlays adopt a new broadcast style: dark translucent panel, thin amber accent bar at the top, custom fonts
- Custom fonts loaded at startup: JetBrains Mono for labels, Saira Semi Condensed for numbers
- Centralized color system: all overlays share the same design tokens

### Changes per overlay
- **Speed** — 18-segment RPM bar (green → amber → red), large speed number, gear in amber
- **Inputs** — vertical T/B/C bars, 3-spoke steering wheel with angle label
- **Tyres** — bars colored by temperature, FL/FR/RL/RR corner labels
- **Standings** — P1/P2/P3 in gold/silver/bronze, best lap in purple, player row highlighted in amber
- **Relative** — class color chip on position, colored gap (blue = ahead, orange = behind)
- **Fuel / VE Calculator** — blue fuel bar, green VE bar, unified table style
- **Main window** — dark panel, amber tab underline, custom drawn gear icon

### Fixed
- Crash at startup when a tyre temperature was 0
- Lock toggle colors were misaligned with the theme

---

## [0.2.0] — Fuel & VE Calculators

### New
- **Fuel Calculator** — fuel bar + table (last lap, 5-lap average, consumption, refuel needed, finish estimate), configurable safety margin
- **VE Calculator** — same as Fuel Calculator but for virtual energy (Hypercar), with fuel ratio display
- **Merge mode** — single toggle: automatically shows the right calculator based on car class (Hypercar / GT3 → VE Calc, others → Fuel Calc)
- Refuel detection: fuel spikes above 2 L are excluded from the consumption history
- Each element of the overlay can be hidden independently (bar, level text, rows, columns)
- Overlay width adjusts automatically to the visible columns

### Removed
- Old basic Fuel overlay replaced by the Fuel Calculator

---

## [0.1.2] — Standings & Relative

### New
- Player row highlight color and opacity are now configurable in Standings and Relative

---

## [0.1.1] — Quality of life improvements

### New
- Opacity control (0–100 %) on all overlays
- **Tyres** — 4 vertical bars (FL/FR/RL/RR): height = remaining wear, color = temperature
- **Fuel** — VE row auto-hides if no virtual energy is detected
- Animated lock toggle: green = free to move, gold = locked in place
- ON / OFF buttons per overlay in the main window

### Changed
- **Standings** — class headers shown as colored badges (HYP / P2 / P3 / GTE / GT3)
- Class colors inspired by WEC: Hypercar red, LMP2 blue, LMP3 purple, GT3 green, GTE orange
- Reduced default overlay sizes to take up less screen space

### Fixed
- Hypercars named "LMH" or "GTP" in-game were appearing below GT3 in the standings
- Overlay border remained visible at 0% opacity

---

## [0.1.0] — Initial release

### New
- Core architecture: live LMU data reading, resizable and draggable overlays
- Overlays: **Speed**, **Inputs**, **Fuel**, **Standings**, **Relative**, **Tyres**
- Main control window with per-overlay enable / disable
- Automatic config saving (positions and parameters)
- Per-overlay settings dialog
- Drag & drop and position lock
- PIT / OUT / GAR badges in Standings and Relative
- Outlap tracking in Relative
