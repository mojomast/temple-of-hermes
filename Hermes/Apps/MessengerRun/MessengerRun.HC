#ifndef MR_MAIN_HC
#define MR_MAIN_HC 1

#define MR_COLS       11
#define MR_ROWS       9
#define MR_CELL       36
#define MR_PLAYER_ROW (MR_ROWS - 1)
#define MR_MAX_OBJ    48

#define MR_NONE       0
#define MR_SCROLL     1
#define MR_STORM      2
#define MR_SEAL       3

I64 mr_ocol[MR_MAX_OBJ];
I64 mr_orow[MR_MAX_OBJ];
I64 mr_okind[MR_MAX_OBJ];
I64 mr_player_col;
I64 mr_score;
I64 mr_best;
I64 mr_lives;
I64 mr_combo;
I64 mr_mult;
I64 mr_delivered;
I64 mr_flash;
I64 mr_msg_t;
I64 mr_frame;
I64 mr_ticks;
Bool mr_running;
Bool mr_paused;
Bool mr_over;
Bool mr_agent;
U8 *mr_msg;
U8 *mr_agent_note;
F64 mr_next_tick;
F64 mr_next_agent;
F64 mr_tick_interval;

RegDft("TinkerOS/MessengerRun", "mr_best=0;\n");
RegExe("TinkerOS/MessengerRun");

I64 MrClamp(I64 v, I64 lo, I64 hi)
{
  if (v < lo)
    return lo;
  if (v > hi)
    return hi;
  return v;
}

U0 MrClearObjs()
{
  I64 i;
  for (i = 0; i < MR_MAX_OBJ; i++)
  {
    mr_ocol[i] = 0;
    mr_orow[i] = 0;
    mr_okind[i] = MR_NONE;
  }
}

U0 MrSpawn(I64 kind, I64 col)
{
  I64 i;
  for (i = 0; i < MR_MAX_OBJ; i++)
    if (mr_okind[i] == MR_NONE)
    {
      mr_okind[i] = kind;
      mr_ocol[i] = MrClamp(col, 0, MR_COLS - 1);
      mr_orow[i] = 0;
      return;
    }
}

U0 MrSay(U8 *msg, I64 frames)
{
  mr_msg = msg;
  mr_msg_t = frames;
}

U0 MrLoseLife()
{
  mr_lives--;
  mr_combo = 0;
  mr_mult = 1;
  mr_flash = 16;
  if (mr_score >= 20)
    mr_score -= 20;
  else
    mr_score = 0;
  MrSay("STORM HIT - SCROLL DROPPED", 90);
  if (mr_lives <= 0)
  {
    mr_lives = 0;
    mr_over = TRUE;
    if (mr_score > mr_best)
      mr_best = mr_score;
    MrSay("RUN ENDED - PRESS ENTER", 100000);
  }
}

U0 MrCollect(I64 kind)
{
  if (kind == MR_SEAL)
  {
    if (mr_lives < 5)
      mr_lives++;
    mr_score += 25;
    MrSay("CADUCEUS SEAL - EXTRA LIFE", 80);
  }
  else
  {
    mr_delivered++;
    mr_combo++;
    mr_mult = 1 + mr_combo / 5;
    if (mr_mult > 6)
      mr_mult = 6;
    mr_score += 10 * mr_mult;
    MrSay("MESSAGE DELIVERED", 55);
  }
  if (mr_score > mr_best)
    mr_best = mr_score;
}

U0 MrNewGame()
{
  I64 i;
  MrClearObjs();
  mr_player_col = MR_COLS / 2;
  mr_score = 0;
  mr_lives = 3;
  mr_combo = 0;
  mr_mult = 1;
  mr_delivered = 0;
  mr_flash = 0;
  mr_ticks = 0;
  mr_frame = 0;
  mr_paused = FALSE;
  mr_over = FALSE;
  mr_tick_interval = 0.62;
  mr_next_tick = tS + 1.0;
  mr_next_agent = tS;
  mr_agent_note = "AUTO: PATROL LANE";
  MrSay("DELIVER THE SCROLLS", 100);
  for (i = 0; i < 3; i++)
    MrSpawn(MR_SCROLL, (mr_player_col + i * 3 + 2) % MR_COLS);
  MrSpawn(MR_STORM, (mr_player_col + 5) % MR_COLS);
}

U0 MrResolve(I64 kind)
{
  if (kind == MR_STORM)
    MrLoseLife;
  else
    MrCollect(kind);
}

U0 MrStep()
{
  I64 i, kind, roll, extra;
  for (i = 0; i < MR_MAX_OBJ; i++)
  {
    kind = mr_okind[i];
    if (kind != MR_NONE)
    {
      mr_orow[i]++;
      if (mr_orow[i] >= MR_ROWS)
      {
        if (kind == MR_SCROLL)
        {
          mr_combo = 0;
          mr_mult = 1;
          MrSay("MESSAGE LOST - COMBO RESET", 65);
        }
        mr_okind[i] = MR_NONE;
      }
      else if (mr_orow[i] == MR_PLAYER_ROW && mr_ocol[i] == mr_player_col)
      {
        mr_okind[i] = MR_NONE;
        MrResolve(kind);
      }
    }
  }
  mr_ticks++;
  roll = RandU16 % 100;
  if (roll < 58)
    MrSpawn(MR_SCROLL, RandU16 % MR_COLS);
  else if (roll < 91)
    MrSpawn(MR_STORM, RandU16 % MR_COLS);
  else if (roll < 96)
    MrSpawn(MR_SEAL, RandU16 % MR_COLS);
  extra = mr_ticks % 7;
  if (extra == 0 && (RandU16 & 1))
    MrSpawn(MR_SCROLL, RandU16 % MR_COLS);
  mr_tick_interval = 0.62 - (mr_ticks / 90) * 0.045;
  if (mr_tick_interval < 0.27)
    mr_tick_interval = 0.27;
  mr_next_tick = tS + mr_tick_interval;
}

U0 MrAgentStep()
{
  I64 i, c, target, target_row, why, danger[MR_COLS];
  for (c = 0; c < MR_COLS; c++)
    danger[c] = 0;
  for (i = 0; i < MR_MAX_OBJ; i++)
    if (mr_okind[i] == MR_STORM)
      if (mr_orow[i] >= MR_PLAYER_ROW - 2)
        danger[mr_ocol[i]] = 1;
  target = -1;
  target_row = -1;
  for (i = 0; i < MR_MAX_OBJ; i++)
    if (mr_okind[i] == MR_SCROLL)
      if (mr_orow[i] > target_row)
      {
        target_row = mr_orow[i];
        target = mr_ocol[i];
      }
  why = 0;
  if (danger[mr_player_col])
  {
    if (mr_player_col > 0 && !danger[mr_player_col - 1])
      mr_player_col--;
    else if (mr_player_col < MR_COLS - 1 && !danger[mr_player_col + 1])
      mr_player_col++;
    why = 1;
  }
  else if (target >= 0)
  {
    if (danger[target])
    {
      if (mr_player_col > 0 && !danger[mr_player_col - 1] &&
          (target < mr_player_col || danger[mr_player_col + 1]))
        mr_player_col--;
      else if (mr_player_col < MR_COLS - 1 && !danger[mr_player_col + 1])
        mr_player_col++;
      why = 2;
    }
    else
    {
      if (mr_player_col < target)
        mr_player_col++;
      else if (mr_player_col > target)
        mr_player_col--;
      why = 3;
    }
  }
  else
  {
    if (mr_player_col < MR_COLS / 2)
      mr_player_col++;
    else if (mr_player_col > MR_COLS / 2)
      mr_player_col--;
    why = 4;
  }
  mr_next_agent = tS + 0.075;
  if (why == 1)
  {
    mr_agent_note = "AUTO: DODGE STORM";
    MrSay("AUTO: DODGE STORM", 12);
  }
  else if (why == 2)
  {
    mr_agent_note = "AUTO: SAFE ROUTE";
    MrSay("AUTO: SAFE ROUTE", 12);
  }
  else if (why == 3)
  {
    mr_agent_note = "AUTO: SEEK SCROLL";
    MrSay("AUTO: SEEK SCROLL", 12);
  }
  else
  {
    mr_agent_note = "AUTO: PATROL LANE";
    MrSay("AUTO: PATROL LANE", 12);
  }
}

U0 MrAgentTick()
{
  if (tS >= mr_next_agent)
    MrAgentStep;
}

U0 MrToggleAgent()
{
  mr_agent = !mr_agent;
  if (mr_agent)
  {
    mr_next_agent = tS;
    mr_agent_note = "AUTO: PATROL LANE";
    MrSay("AGENT PLAY ON - PRESS A FOR HUMAN", 100);
  }
  else
    MrSay("HUMAN CONTROL ON", 70);
}

U0 MrStars(CDC *dc, I64 w, I64 h)
{
  I64 i, x, y;
  for (i = 0; i < 84; i++)
  {
    x = (i * 97 + 31) % w;
    y = (i * 57 + 17) % h;
    if ((i & 3) == 0)
      dc->color = LTBLUE;
    else if ((i & 3) == 1)
      dc->color = CYAN;
    else
      dc->color = DKGRAY;
    GrPlot(dc, x, y);
    if ((i & 7) == 0)
      GrPlot(dc, x + 1, y);
  }
}

U0 MrScroll(CDC *dc, I64 x, I64 y)
{
  dc->color = BROWN;
  GrRect(dc, x + 8, y + 10, 20, 16);
  dc->color = YELLOW;
  GrLine(dc, x + 10, y + 13, x + 25, y + 13);
  GrLine(dc, x + 10, y + 17, x + 25, y + 17);
  GrLine(dc, x + 10, y + 21, x + 22, y + 21);
  dc->color = LTCYAN;
  GrLine(dc, x + 8, y + 10, x + 8, y + 26);
  GrLine(dc, x + 27, y + 10, x + 27, y + 26);
}

U0 MrStorm(CDC *dc, I64 x, I64 y)
{
  dc->color = DKGRAY;
  GrFillCircle(dc, x + 18, y + 19, 0, 22);
  GrFillCircle(dc, x + 11, y + 16, 0, 16);
  GrFillCircle(dc, x + 25, y + 16, 0, 16);
  dc->color = LTRED;
  GrLine(dc, x + 18, y + 20, x + 14, y + 27);
  GrLine(dc, x + 14, y + 27, x + 19, y + 26);
  GrLine(dc, x + 19, y + 26, x + 15, y + 33);
}

U0 MrSeal(CDC *dc, I64 x, I64 y)
{
  dc->color = LTCYAN;
  GrLine(dc, x + 18, y + 7, x + 27, y + 18);
  GrLine(dc, x + 27, y + 18, x + 18, y + 29);
  GrLine(dc, x + 18, y + 29, x + 9, y + 18);
  GrLine(dc, x + 9, y + 18, x + 18, y + 7);
  dc->color = YELLOW;
  GrLine(dc, x + 18, y + 12, x + 18, y + 24);
  GrLine(dc, x + 13, y + 16, x + 23, y + 16);
}

U0 MrPlayer(CDC *dc, I64 x, I64 y)
{
  I64 bob;
  bob = (mr_frame >> 2) & 1;
  dc->color = WHITE;
  GrLine(dc, x + 13, y + 14 + bob, x + 2, y + 9 + bob);
  GrLine(dc, x + 13, y + 17 + bob, x + 2, y + 22 + bob);
  GrLine(dc, x + 23, y + 14 + bob, x + 34, y + 9 + bob);
  GrLine(dc, x + 23, y + 17 + bob, x + 34, y + 22 + bob);
  dc->color = YELLOW;
  GrFillCircle(dc, x + 18, y + 17 + bob, 0, 20);
  dc->color = LTRED;
  GrFillCircle(dc, x + 18, y + 8 + bob, 0, 11);
  dc->color = BLACK;
  GrPlot(dc, x + 16, y + 7 + bob);
  GrPlot(dc, x + 20, y + 7 + bob);
  dc->color = LTCYAN;
  GrRect(dc, x + 13, y + 27 + bob, 10, 4);
  dc->color = WHITE;
  GrLine(dc, x + 18, y + 17 + bob, x + 28, y + 11 + bob);
  GrLine(dc, x + 28, y + 11 + bob, x + 31, y + 16 + bob);
}

U0 MrBoard(CDC *dc, I64 bx, I64 by)
{
  I64 i, r, c, x, y, kind;
  dc->color = BROWN;
  GrRect(dc, bx - 4, by - 4, MR_COLS * MR_CELL + 8, MR_ROWS * MR_CELL + 8);
  dc->color = BLACK;
  GrRect(dc, bx, by, MR_COLS * MR_CELL, MR_ROWS * MR_CELL);
  dc->color = DKGRAY;
  for (c = 1; c < MR_COLS; c++)
    GrLine(dc, bx + c * MR_CELL, by, bx + c * MR_CELL, by + MR_ROWS * MR_CELL);
  for (r = 1; r < MR_ROWS; r++)
    GrLine(dc, bx, by + r * MR_CELL, bx + MR_COLS * MR_CELL, by + r * MR_CELL);
  dc->color = LTGRAY;
  GrLine(dc, bx, by + MR_PLAYER_ROW * MR_CELL, bx + MR_COLS * MR_CELL,
    by + MR_PLAYER_ROW * MR_CELL);
  dc->color = BLUE;
  GrRect(dc, bx, by + MR_PLAYER_ROW * MR_CELL, MR_COLS * MR_CELL, MR_CELL);
  dc->color = DKGRAY;
  for (r = 1; r < MR_ROWS; r++)
    GrLine(dc, bx, by + r * MR_CELL, bx + MR_COLS * MR_CELL, by + r * MR_CELL);
  for (i = 0; i < MR_MAX_OBJ; i++)
  {
    kind = mr_okind[i];
    if (kind != MR_NONE)
    {
      x = bx + mr_ocol[i] * MR_CELL;
      y = by + mr_orow[i] * MR_CELL;
      if (kind == MR_SCROLL)
        MrScroll(dc, x, y);
      else if (kind == MR_STORM)
        MrStorm(dc, x, y);
      else
        MrSeal(dc, x, y);
    }
  }
  MrPlayer(dc, bx + mr_player_col * MR_CELL, by + MR_PLAYER_ROW * MR_CELL);
}

U0 MrHud(CDC *dc, I64 hx, I64 by)
{
  I64 i, hy;
  dc->color = LTGRAY;
  GrRect(dc, hx, by - 4, 172, MR_ROWS * MR_CELL + 8);
  dc->color = BLACK;
  GrRect(dc, hx + 2, by - 2, 168, MR_ROWS * MR_CELL + 4);
  hy = by + 8;
  dc->color = YELLOW;
  GrPrint(dc, hx + 12, hy, "SCORE");
  dc->color = WHITE;
  GrPrint(dc, hx + 12, hy + 13, "%d", mr_score);
  hy += 42;
  dc->color = LTGRAY;
  GrPrint(dc, hx + 12, hy, "BEST");
  dc->color = LTCYAN;
  GrPrint(dc, hx + 12, hy + 13, "%d", mr_best);
  hy += 42;
  dc->color = LTGRAY;
  GrPrint(dc, hx + 12, hy, "DELIVERED");
  dc->color = LTGREEN;
  GrPrint(dc, hx + 12, hy + 13, "%d", mr_delivered);
  hy += 42;
  dc->color = LTGRAY;
  GrPrint(dc, hx + 12, hy, "COMBO");
  dc->color = YELLOW;
  GrPrint(dc, hx + 12, hy + 13, "x%d", mr_mult);
  hy += 42;
  dc->color = LTGRAY;
  GrPrint(dc, hx + 12, hy, "LIVES");
  for (i = 0; i < 5; i++)
  {
    if (i < mr_lives)
      dc->color = LTRED;
    else
      dc->color = DKGRAY;
    GrFillCircle(dc, hx + 18 + i * 18, hy + 24, 0, 10);
  }
  hy += 46;
  if (mr_agent)
  {
    dc->color = LTCYAN;
    GrPrint(dc, hx + 12, hy, "AGENT PLAY");
    dc->color = CYAN;
    GrPrint(dc, hx + 12, hy + 13, "AUTOPILOT ON");
    dc->color = LTCYAN;
    GrPrint(dc, hx + 12, hy + 27, "%s", mr_agent_note);
  }
  else
  {
    dc->color = WHITE;
    GrPrint(dc, hx + 12, hy, "HUMAN PLAY");
    dc->color = LTGRAY;
    GrPrint(dc, hx + 12, hy + 13, "PRESS A FOR AGENT");
  }
}

U0 MrMessage(CDC *dc, I64 bx, I64 by)
{
  I64 w;
  if (mr_msg_t <= 0)
    return;
  w = StrLen(mr_msg) * FONT_WIDTH;
  dc->color = DKGRAY;
  GrRect(dc, bx + (MR_COLS * MR_CELL - w) / 2 - 8, by + 12, w + 16, 22);
  dc->color = YELLOW;
  GrPrint(dc, bx + (MR_COLS * MR_CELL - w) / 2, by + 18, "%s", mr_msg);
}

U0 MrOverlay(CDC *dc, I64 bx, I64 by)
{
  I64 w;
  if (mr_paused && !mr_over)
  {
    w = 11 * FONT_WIDTH;
    dc->color = BLACK;
    GrRect(dc, bx + MR_COLS * MR_CELL / 2 - w / 2 - 10,
      by + MR_ROWS * MR_CELL / 2 - 34, w + 20, 56);
    dc->color = YELLOW;
    GrPrint(dc, bx + MR_COLS * MR_CELL / 2 - w / 2,
      by + MR_ROWS * MR_CELL / 2 - 22, "PAUSED");
    dc->color = WHITE;
    GrPrint(dc, bx + MR_COLS * MR_CELL / 2 - 8 * FONT_WIDTH,
      by + MR_ROWS * MR_CELL / 2 + 2, "P TO RESUME");
  }
  if (mr_over)
  {
    dc->color = BLACK;
    GrRect(dc, bx + 20, by + MR_ROWS * MR_CELL / 2 - 48,
      MR_COLS * MR_CELL - 40, 96);
    dc->color = LTRED;
    GrPrint(dc, bx + MR_COLS * MR_CELL / 2 - 9 * FONT_WIDTH / 2,
      by + MR_ROWS * MR_CELL / 2 - 32, "RUN ENDED");
    dc->color = WHITE;
    GrPrint(dc, bx + MR_COLS * MR_CELL / 2 - 13 * FONT_WIDTH / 2,
      by + MR_ROWS * MR_CELL / 2 - 8, "ENTER: RUN AGAIN");
    dc->color = LTGRAY;
    GrPrint(dc, bx + MR_COLS * MR_CELL / 2 - 8 * FONT_WIDTH / 2,
      by + MR_ROWS * MR_CELL / 2 + 14, "ESC: QUIT");
  }
}

U0 MrDrawIt(CTask *task, CDC *dc)
{
  I64 w, h, bx, by, hx;
  w = task->pix_width;
  h = task->pix_height;
  dc->color = BLACK;
  GrRect(dc, 0, 0, w, h);
  MrStars(dc, w, h);
  bx = (w - (MR_COLS * MR_CELL + 172 + 20)) / 2;
  if (bx < 20)
    bx = 20;
  by = 96;
  dc->color = YELLOW;
  GrPrint(dc, bx, 44, "MESSENGER RUN");
  dc->color = LTCYAN;
  GrPrint(dc, bx + 214, 44, "THE TEMPLE OF HERMES");
  dc->color = BROWN;
  GrLine(dc, bx, 70, bx + MR_COLS * MR_CELL + 172 + 20, 70);
  dc->color = DKGRAY;
  GrLine(dc, bx, 72, bx + MR_COLS * MR_CELL + 172 + 20, 72);
  MrBoard(dc, bx, by);
  hx = bx + MR_COLS * MR_CELL + 20;
  MrHud(dc, hx, by);
  MrMessage(dc, bx, by);
  MrOverlay(dc, bx, by);
  dc->color = LTGRAY;
  GrPrint(dc, bx, by + MR_ROWS * MR_CELL + 14,
    "ARROWS MOVE   A AGENT   P PAUSE   ENTER RESTART   ESC QUIT");
  if (mr_flash > 0)
  {
    dc->color = LTRED;
    GrRect(dc, bx - 4, by - 4, MR_COLS * MR_CELL + 8, 3);
    GrRect(dc, bx - 4, by + MR_ROWS * MR_CELL + 1, MR_COLS * MR_CELL + 8, 3);
  }
  if (mr_agent)
  {
    dc->color = LTCYAN;
    GrPrint(dc, bx, 18, "AGENT-PLAY DEMO");
  }
  else
  {
    dc->color = LTGRAY;
    GrPrint(dc, bx, 18, "HUMAN ARCADE");
  }
  mr_frame++;
}

U0 MessengerRun(Bool agent = FALSE)
{
  I64 arg1, arg2;
  SettingsPush;
  Fs->text_attr = BLACK << 4 + WHITE;
  MenuPush(
    "File {"
    "  Exit(,CH_ESC);"
    "}"
    "Game {"
    "  Restart(,'\n');"
    "  Pause(,'P');"
    "  AgentPlay(,'A');"
    "}"
  );
  AutoComplete(0);
  WinBorder;
  WinMax;
  DocCursor;
  DocClear;
  mr_agent = agent;
  mr_running = TRUE;
  MrNewGame;
  if (mr_agent)
    MrSay("AGENT PLAY ON - PRESS A FOR HUMAN", 140);
  Fs->draw_it = &MrDrawIt;
  arg1 = 0;
  arg2 = 0;
  try
  {
    while (mr_running)
    {
      switch (ScanMsg(&arg1, &arg2, 1 << MSG_KEY_DOWN))
      {
      case MSG_KEY_DOWN:
        if (arg1 == CH_ESC || arg1 == CH_SHIFT_ESC || arg1 == CH_CTRLQ)
          goto mr_done;
        if (arg1 == '\n')
        {
          MrNewGame;
          break;
        }
        if (arg1 == 'P' || arg1 == 'p')
        {
          if (!mr_over)
            mr_paused = !mr_paused;
          break;
        }
        if (arg1 == 'A' || arg1 == 'a')
        {
          MrToggleAgent;
          break;
        }
        if (!mr_over && !mr_paused)
        {
          switch (arg2.u8[0])
          {
          case SC_CURSOR_LEFT:
            if (mr_player_col > 0)
              mr_player_col--;
            break;
          case SC_CURSOR_RIGHT:
            if (mr_player_col < MR_COLS - 1)
              mr_player_col++;
            break;
          }
        }
        break;
      }
      if (!mr_over && !mr_paused)
      {
        if (mr_agent)
          MrAgentTick;
        if (tS >= mr_next_tick)
          MrStep;
      }
      if (mr_flash > 0)
        mr_flash--;
      if (mr_msg_t > 0 && mr_msg_t < 99999)
        mr_msg_t--;
      Sleep(16);
    }
mr_done:
  }
  catch
    PutExcept;
  Fs->draw_it = NULL;
  if (mr_score > mr_best)
    mr_best = mr_score;
  RegWrite("TinkerOS/MessengerRun", "mr_best=%d;\n", mr_best);
  MenuPop;
  SettingsPop;
  DocClear;
}

#endif
