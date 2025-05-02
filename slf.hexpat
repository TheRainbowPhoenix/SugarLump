struct Entry {
  u8   nameLen;               // length of the name
  char name[nameLen];         // e.g. "Chapter0|Dummy"
  char data[8];
} [[hex::visualize("list", name)]];

struct IMAGE {
    char magic[10];  
    u8 compressionType;
    u32 stat1;
    u32 stat2;


    u32 field1; // 0 
    u32 field2; // 0
    
    u32 field3; // width
    u32 field4; // height
    
    u32 dataSize;
    u8 pixelData[dataSize];
    u8 frameCount;
};

struct SLF {
  char magic[16];              // "SugarLumpFile100"
  u32  count;              // number of lumps
  Entry entries[count];        // directory
  IMAGE images[count];
} [[hex::visualize("list", magic, count, entries, images)]];


SLF file @ 0x0;