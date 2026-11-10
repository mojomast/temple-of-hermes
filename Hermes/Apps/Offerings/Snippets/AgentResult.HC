// AgentResult.HC - write a tiny result file an agent can read.
U0 DemoResult(U8 *id)
{
  U8 *path,*line,*use;
  DirMk("C:/Tmp");
  DirMk("C:/Tmp/Offerings");
  DirMk("C:/Tmp/Offerings/Results");
  path="C:/Tmp/Offerings/Results/demo.json";
  use=id;
  if (!use)
    use="demo";
  line=MStrPrint("{\"ok\":1,\"id\":\"%s\"}\n",use);
  FileWrite(path,line,StrLen(line));
  "Wrote %s\n",path;
  Free(line);
}
