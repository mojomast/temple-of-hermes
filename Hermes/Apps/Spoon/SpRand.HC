#ifndef SP_RAND_HC
#define SP_RAND_HC

static U64 sp_seed=1;

U0 SpSeed(I64 s)
{
  sp_seed=s;
}

I64 SpRand()
{
  I64 r;
  sp_seed=sp_seed*6364136223846793005+1442695040888963407;
  r=sp_seed;
  r>>=33;
  return r;
}

I64 SpRandRange(I64 lo,I64 hi)
{
  if (hi<=lo)
    return lo;
  return lo+SpRand()%(hi-lo+1);
}

#endif
