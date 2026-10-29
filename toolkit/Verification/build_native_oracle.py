from pathlib import Path
import re,json
import argparse
parser=argparse.ArgumentParser()
parser.add_argument('--source',type=Path,required=True)
parser.add_argument('--output',type=Path,default=Path(__file__).resolve().parent)
args=parser.parse_args()
r=args.output
source=args.source.read_text()
body=source.split('void EmitFloatCompareFlags(IOperand left, IOperand right)',1)[1].split('void EmitResultFlags',1)[0]
ops=re.findall(r'Add\(address, OpCode\.(\w+), (\w+), (\w+), (\w+|Imm\(0\))\);',body);assert len(ops)==6
symbols={'CheckLess':'<','CheckEqual':'==','CheckNotEqual':'!=','Or':'|','And':'&'}
model=['static unsigned emitted_flags(float left, float right) {']
for op,d,a,b in ops:model.append(f' unsigned {d} = ({a} {symbols[op]} {"0" if b=="Imm(0)" else b});')
model+=[' return flagN*8+flagZ*4+flagC*2+flagV;','}']
conditionBody=source.split('IOperand EmitCondition(Arm64ConditionCode condition)',1)[1].split('void EmitConditionalAssign',1)[0]
codes={'EQ':0,'NE':1,'CS':2,'CC':3,'MI':4,'PL':5,'VS':6,'VC':7,'HI':8,'LS':9,'GE':10,'LT':11,'GT':12,'LE':13}
condition=['static unsigned emitted_condition(unsigned flags, unsigned condition) { unsigned flagN=(flags>>3)&1, flagZ=(flags>>2)&1, flagC=(flags>>1)&1, flagV=flags&1, temp=0,temp2=0; switch(condition) {']
for name,code in codes.items():
 match=re.search(r'case Arm64ConditionCode\.'+name+r':(.*?)return (\w+);',conditionBody,re.S);assert match,name
 statement=match.group(1);result=match.group(2);condition.append(f'case {code}:')
 for op,d,a,b in re.findall(r'Add\(address, OpCode\.(\w+), (\w+), (\w+), (\w+|Imm\(0\))\);',statement):condition.append(f' {d}=({a} {symbols[op]} {"0" if b=="Imm(0)" else b});')
 assert 'OpCode.Not,' not in statement
 condition.append(' return '+result+';')
condition+=['default: return 1;','}}']
fragment=json.loads((Path(__file__).resolve().parent/'fp-branch-fixture.json').read_text());assert fragment['leftRegister']==0 and fragment['rightRegister']==1
assembly=['.text','.globl _fp_flags','_fp_flags:','fcmp s0, s1','mrs x0, nzcv','ret','.globl _fp_conditional','_fp_conditional:','cmp w0, #0','fccmp s0, s1, #5, eq','mrs x0, nzcv','ret','.globl _sample_branch','_sample_branch:',f'.inst {hex(fragment["compareWord"])}','b.lt L_sample_taken','mov w0, #0','ret','L_sample_taken:','mov w0, #1','ret']
for name,code in codes.items():assembly += [f'.globl _fp_cond_{code}',f'_fp_cond_{code}:','fcmp s0,s1',f'cset w0,{name.lower()}','ret']
(r/'native-fp-oracle.s').write_text('\n'.join(assembly)+'\n')
header='#include <stdint.h>\n#include <stdio.h>\nextern uint64_t fp_flags(float,float);\nextern uint64_t fp_conditional(float,float,int);\nextern unsigned sample_branch(float,float);\n'
for code in codes.values():header+=f'extern unsigned fp_cond_{code}(float,float);\n'
main='''int main(void) {
 uint32_t bits[]={0x00000000,0x80000000,0x3F800000,0xBF800000,0x00800000,0x00000001,0x7F7FFFFF,0xFF7FFFFF,0x7F800000,0xFF800000,0x7FC00000};
 unsigned passed=0;
 for(unsigned i=0;i<11;i++)for(unsigned j=0;j<11;j++){
  union {uint32_t bits;float value;} a={.bits=bits[i]},b={.bits=bits[j]};
  unsigned expected=emitted_flags(a.value,b.value);
  unsigned native=(unsigned)(fp_flags(a.value,b.value)>>28)&15;
  if(native!=expected){printf("NZCV mismatch %u %u: %u %u\\n",i,j,native,expected);return 1;}passed++;
  if(((fp_conditional(a.value,b.value,0)>>28)&15)!=expected){puts("FCCMP enabled mismatch");return 1;}passed++;
  if(((fp_conditional(a.value,b.value,1)>>28)&15)!=5){puts("FCCMP fallback mismatch");return 1;}passed++;
  if(sample_branch(a.value,b.value)!=emitted_condition(expected,11)){puts("Sample branch mismatch");return 1;}passed++;
'''
for code in codes.values():main+=f'  if(fp_cond_{code}(a.value,b.value)!=emitted_condition(expected,{code})){{printf("Condition {code} mismatch %u %u\\n",i,j);return 1;}}passed++;\n'
main+=' }\n printf("{\\\"checks\\\":%u,\\\"nativeARM64\\\":true,\\\"NaNIncluded\\\":true,\\\"scope\\\":\\\"FP flag and condition lowering, synthetic compare/branch fixture; not full gameplay equivalence\\\"}\\n",passed);return 0;\n}\n'
(r/'native-fp-oracle.c').write_text(header+'\n'.join(model)+'\n'+'\n'.join(condition)+'\n'+main)
(r/'fp-branch-fixture.json').write_text(json.dumps(fragment,indent=2))
