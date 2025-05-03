struct LStr {
    u8 size;
    char data[size];
};

struct IMAGE {
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

struct AMapInfo {
    LStr mapInfos;
    
    // data
    u32 stat1;
    u32 stat2;
    
}  [[hex::visualize("str", mapInfos)]];


struct MapName {
    LStr mapName;
    u16 a1;
    u16 a2;
};

struct MapInfos {
    u8 s1;
    u8 s2; // size ?
    u8 s3;
    
    MapName names[s2];
};

struct PropKV {
    LStr keyName;
    LStr keyVal;
};

struct LayerObject {
    LStr s1; 
    LStr group_value;
    
    float x;
    // u16 a1; // 00 00
    // u16 a2; // 80 41
    float y;
    // u16 a3; // 00 00
    // u16 a4; // 80 41
    float w;
    // u16 a5; // 00 00
    // u16 a6; // 80 41
    float h;
    // u16 a7; // 00 00
    // u16 a8; // 80 41
    
    u16 a9; // FF FF
    u16 a10; // 00 00
    
    PropKV kv[a10];
};

struct LayerData {
    LStr type; // if 'Title' => Title Layer
    // u8 szType;
    // char type[szType];
    
    
    if (type.data == "Tile") {
    
        LStr floor;
        
        u16 propCount;
        
        PropKV kv[propCount];
        // if depth => atof
        
        // LStr depth; 
        // LStr depthVal;
        
        u32 e1;
        
        u16 width;
        u16 height;
        
        u16 tileIDs[width * height];
        u16 colIDs[width * height];
    }
    
    if (type.data == "Object") {
    
        LStr layer_name;
        
        u16 group_count;
        u16 items_count;
        
        LayerObject objects[items_count];
        
    }
};

struct Ray {
    u32 x;
    u32 y;
    u32 w;
    u32 h;
    u32 flags;
};

struct RayCastData {
    u32 rayCount;
    
    Ray ray[rayCount];
    
    u32 colCount;
    u32 rowCount;
    
    u32 unk0;
    u32 unk1;
    
    u32 segs[colCount * rowCount];
    
    u8 unk3[rowCount * 16];
    u16 a1;
    u16 a2;
    u16 a3;
};

struct PackedElem {
    char header[10];
    
    if (header == "MAPINFO000") {
        MapInfos data;
    }
    
    if (header == "LAYERDATA1") {
        LayerData data;
    }
    
    if (header == "RCEDATA000") {
        RayCastData data;
    }
    
    if (header == "IMAGE00000") {
        IMAGE data;
    }

};

struct SLF {
  char magic[16];              // "SugarLumpFile100"
  u32  count;              // number of lumps
  AMapInfo aMapInfo[count];
  
  PackedElem elem[count];
 
  
  

} [[hex::visualize("list", magic, count, aMapInfo)]];


SLF file @ 0x0;