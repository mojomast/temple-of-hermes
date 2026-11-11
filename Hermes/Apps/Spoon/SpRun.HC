#ifndef SP_RUN_HC
#define SP_RUN_HC

U0 SpoonRun()
{
  SpoonTask(NULL);
}

U0 Spoon(Bool agent=FALSE)
{
  if (agent)
    SpoonAgent(NULL);
  else
    SpoonRun;
}

#endif
