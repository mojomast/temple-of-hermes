#ifndef SP_RUN_HC
#define SP_RUN_HC

U0 SpoonRun()
{
  Spawn(&SpoonTask,NULL,"Spoon");
}

U0 Spoon(Bool agent=FALSE)
{
  if (agent)
    SpoonAgent(NULL);
  else
    SpoonRun;
}

#endif
