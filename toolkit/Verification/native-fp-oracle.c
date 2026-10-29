#include <stdint.h>
#include <stdio.h>
extern uint64_t fp_flags(float,float);
extern uint64_t fp_conditional(float,float,int);
extern unsigned sample_branch(float,float);
extern unsigned fp_cond_0(float,float);
extern unsigned fp_cond_1(float,float);
extern unsigned fp_cond_2(float,float);
extern unsigned fp_cond_3(float,float);
extern unsigned fp_cond_4(float,float);
extern unsigned fp_cond_5(float,float);
extern unsigned fp_cond_6(float,float);
extern unsigned fp_cond_7(float,float);
extern unsigned fp_cond_8(float,float);
extern unsigned fp_cond_9(float,float);
extern unsigned fp_cond_10(float,float);
extern unsigned fp_cond_11(float,float);
extern unsigned fp_cond_12(float,float);
extern unsigned fp_cond_13(float,float);
static unsigned emitted_flags(float left, float right) {
 unsigned flagN = (left < right);
 unsigned flagZ = (left == right);
 unsigned flagC = (flagN == 0);
 unsigned unorderedLeft = (left != left);
 unsigned unorderedRight = (right != right);
 unsigned flagV = (unorderedLeft | unorderedRight);
 return flagN*8+flagZ*4+flagC*2+flagV;
}
static unsigned emitted_condition(unsigned flags, unsigned condition) { unsigned flagN=(flags>>3)&1, flagZ=(flags>>2)&1, flagC=(flags>>1)&1, flagV=flags&1, temp=0,temp2=0; switch(condition) {
case 0:
 return flagZ;
case 1:
 temp=(flagZ == 0);
 return temp;
case 2:
 return flagC;
case 3:
 temp=(flagC == 0);
 return temp;
case 4:
 return flagN;
case 5:
 temp=(flagN == 0);
 return temp;
case 6:
 return flagV;
case 7:
 temp=(flagV == 0);
 return temp;
case 8:
 temp=(flagZ == 0);
 temp=(flagC & temp);
 return temp;
case 9:
 temp=(flagC == 0);
 temp=(temp | flagZ);
 return temp;
case 10:
 temp=(flagN == flagV);
 return temp;
case 11:
 temp=(flagN == flagV);
 temp=(temp == 0);
 return temp;
case 12:
 temp=(flagN == flagV);
 temp2=(flagZ == 0);
 temp=(temp & temp2);
 return temp;
case 13:
 temp=(flagN == flagV);
 temp=(temp == 0);
 temp=(temp | flagZ);
 return temp;
default: return 1;
}}
int main(void) {
 uint32_t bits[]={0x00000000,0x80000000,0x3F800000,0xBF800000,0x00800000,0x00000001,0x7F7FFFFF,0xFF7FFFFF,0x7F800000,0xFF800000,0x7FC00000};
 unsigned passed=0;
 for(unsigned i=0;i<11;i++)for(unsigned j=0;j<11;j++){
  union {uint32_t bits;float value;} a={.bits=bits[i]},b={.bits=bits[j]};
  unsigned expected=emitted_flags(a.value,b.value);
  unsigned native=(unsigned)(fp_flags(a.value,b.value)>>28)&15;
  if(native!=expected){printf("NZCV mismatch %u %u: %u %u\n",i,j,native,expected);return 1;}passed++;
  if(((fp_conditional(a.value,b.value,0)>>28)&15)!=expected){puts("FCCMP enabled mismatch");return 1;}passed++;
  if(((fp_conditional(a.value,b.value,1)>>28)&15)!=5){puts("FCCMP fallback mismatch");return 1;}passed++;
  if(sample_branch(a.value,b.value)!=emitted_condition(expected,11)){puts("Sample branch mismatch");return 1;}passed++;
  if(fp_cond_0(a.value,b.value)!=emitted_condition(expected,0)){printf("Condition 0 mismatch %u %u\n",i,j);return 1;}passed++;
  if(fp_cond_1(a.value,b.value)!=emitted_condition(expected,1)){printf("Condition 1 mismatch %u %u\n",i,j);return 1;}passed++;
  if(fp_cond_2(a.value,b.value)!=emitted_condition(expected,2)){printf("Condition 2 mismatch %u %u\n",i,j);return 1;}passed++;
  if(fp_cond_3(a.value,b.value)!=emitted_condition(expected,3)){printf("Condition 3 mismatch %u %u\n",i,j);return 1;}passed++;
  if(fp_cond_4(a.value,b.value)!=emitted_condition(expected,4)){printf("Condition 4 mismatch %u %u\n",i,j);return 1;}passed++;
  if(fp_cond_5(a.value,b.value)!=emitted_condition(expected,5)){printf("Condition 5 mismatch %u %u\n",i,j);return 1;}passed++;
  if(fp_cond_6(a.value,b.value)!=emitted_condition(expected,6)){printf("Condition 6 mismatch %u %u\n",i,j);return 1;}passed++;
  if(fp_cond_7(a.value,b.value)!=emitted_condition(expected,7)){printf("Condition 7 mismatch %u %u\n",i,j);return 1;}passed++;
  if(fp_cond_8(a.value,b.value)!=emitted_condition(expected,8)){printf("Condition 8 mismatch %u %u\n",i,j);return 1;}passed++;
  if(fp_cond_9(a.value,b.value)!=emitted_condition(expected,9)){printf("Condition 9 mismatch %u %u\n",i,j);return 1;}passed++;
  if(fp_cond_10(a.value,b.value)!=emitted_condition(expected,10)){printf("Condition 10 mismatch %u %u\n",i,j);return 1;}passed++;
  if(fp_cond_11(a.value,b.value)!=emitted_condition(expected,11)){printf("Condition 11 mismatch %u %u\n",i,j);return 1;}passed++;
  if(fp_cond_12(a.value,b.value)!=emitted_condition(expected,12)){printf("Condition 12 mismatch %u %u\n",i,j);return 1;}passed++;
  if(fp_cond_13(a.value,b.value)!=emitted_condition(expected,13)){printf("Condition 13 mismatch %u %u\n",i,j);return 1;}passed++;
 }
 printf("{\"checks\":%u,\"nativeARM64\":true,\"NaNIncluded\":true,\"scope\":\"FP flag and condition lowering, synthetic compare/branch fixture; not full gameplay equivalence\"}\n",passed);return 0;
}
