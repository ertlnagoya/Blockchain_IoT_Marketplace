use std::str::FromStr;

#[derive(Debug)]
pub enum ScriptFile {
    CompressVideo,
    ExtractImage,
    InferHumanCount,
    Raw,
    Register,
    ImageZip
}

impl ScriptFile {
    pub fn get_script_file_name(&self) -> &'static str {
        match self {
            ScriptFile::CompressVideo => "compress_video.py",
            ScriptFile::ExtractImage => "extract_frame.py",
            ScriptFile::InferHumanCount => "count_people.py",
            ScriptFile::Raw => "raw.py",
            ScriptFile::Register => "register.py",
            ScriptFile::ImageZip => "image_zip.py",
        }
    }
}

impl FromStr for ScriptFile {
    type Err = ();

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        match s {
            "CompressVideo" => Ok(ScriptFile::CompressVideo),
            "ExtractImage" => Ok(ScriptFile::ExtractImage),
            "InferHumanCount" => Ok(ScriptFile::InferHumanCount),
            "Raw" => Ok(ScriptFile::Raw),
            "Register" => Ok(ScriptFile::Register),
            "ImageZip" => Ok(ScriptFile::ImageZip),
            _ => unimplemented!("Invalid script file name: {}", s),
        }
    }
}
