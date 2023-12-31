// http://localhost:3000/

// imports
const express = require("express");
const multer = require('multer');
const path = require('path');
const { spawn } = require('child_process')
const app = express();
const port = 3000

const executePython = async (script, args) => {
    const arguments = args.map(arg => arg.toString());

    const py = spawn("python", [script, ...arguments]);

    const result = await new Promise((resolve, reject)=>{
        let output;

        // Get output from python script 
        py.stdout.on('data', (data)=>{
            output = JSON.parse(data);
        })

        // Handle errors
        py.stderr.on("data",(data) =>{
            console.error(`[python] Error occured: ${data}`);
            reject(`Error occured in ${script}`);
        });

        py.on("exit", (code)=>{
            console.log(`Child process exited with code ${code}`);
            resolve(output);
        });
    });

    return result;
}

// Static Files
app.use(express.urlencoded({ extended: true }));
app.use(express.json());
app.use(express.static('public'))
app.use('/css', express.static(__dirname + 'public/css'))
app.use('/js', express.static(__dirname + 'public/js'))
app.use('/image', express.static(__dirname + 'public/image'))

app.get('/', (req, res)=>{
    res.sendFile(__dirname + '/html/main.html')
})

/// ==================================================== Jiun Ann .html ======================================================================= ///
app.get('/ja', (req, res)=>{
    res.sendFile(__dirname + '/html/ja.html')
})

// --- Daylight Prediction --- //
app.post('/predict', async function(req, res) {
    var curtain_perc = req.body.data;
    try {
        const processedData = await executePython('python/ja_scripts/predictDaylight.py', [curtain_perc]);
        res.json({ processedData });

    } catch (error) {
        res.status(500).json({ error: error }); 
    }
});

// --- Light Simulation --- //
app.post('/simulate', async function(req, res) {
    var zone_spec = req.body.zone_spec;
    var targetcct = req.body.inputcct;
    var targetplux = req.body.inputplux;
    var targetmedi = req.body.inputmedi;
    try {
        const processedData = await executePython('python/ja_scripts/light_simulate.py', [zone_spec, targetcct, targetplux, targetmedi]);
        res.json({ processedData }); 
        console.log(processedData)

    } catch (error) {
        res.status(500).json({ error: error }); 
    }
});


/// ==================================================== Music & Light.html ======================================================================= ///
const storage = multer.diskStorage({
    destination: function (req, file, cb) {
        cb(null, 'python/'); // Specify the folder where uploaded files will be stored
    },
    filename: function (req, file, cb) {
        cb(null, file.originalname); // Use the original filename
    },
});

// Define a custom file filter function for MP3 files
const fileFilter = (req, file, cb) => {
    if (file.mimetype === 'audio/mpeg' || file.mimetype === 'audio/mp3') {
        cb(null, true); // Accept the file
    } else {
        cb(new Error('File type not supported. Please upload an MP3 file.'), false);
    }
};

const upload = multer({ storage, fileFilter });

app.get('/audio', (req, res)=>{
    res.sendFile(__dirname + '/html/music.html')
})

app.post('/upload', upload.single('file'), (req, res) => {
    if (!req.file) {
        return res.send('No file uploaded.');
    }
    return res.send('File uploaded successfully.');
});

app.post('/getMusic_light', async function(req, res) {
    var music = req.body.inputmusic

    try {
        const processedData = await executePython('python/disco.py', [music]);
        res.json({ processedData }); 
        console.log(processedData)

    } catch (error) {
        res.status(500).json({ error: error }); 
    }
})


/// ==================================================== Data Collection.html ======================================================================= ///
app.get('/collect', (req, res)=>{
    res.sendFile(__dirname + '/html/collect.html')
})

app.post('/get_selfcali', async function(req, res) {
    var bri_min = req.body.inputbri_min;
    var bri_max = req.body.inputbri_max;
    var bri_step = req.body.inputbri_step;
    var cct_min = req.body.inputcct_min;
    var cct_max = req.body.inputcct_max;
    var cct_step = req.body.inputcct_step;

    if (bri_min != "" && bri_min >= 5 && bri_min <= 250 && bri_min != bri_max){
        console.log("Bri min: " + bri_min);

        if(bri_max != "" && bri_max >= 5 && bri_max <= 250 && bri_max != bri_min){
            console.log("Bri max: " + bri_max);
            console.log("Bri step: " + bri_step);
            if(cct_min != "" && cct_min >= 2000 && cct_min <= 6500 && cct_min != cct_max){
                console.log("CCT min: " + cct_min);
                if(cct_max != "" && cct_max >= 2000 && cct_max <= 6500 && cct_max != cct_min){
                    console.log("CCT min: " + cct_max);
                    console.log("CCT step: " + cct_step);
                    try {
                        const processedData = await executePython('python/lightsensor_mlv.py', [bri_min, bri_max, bri_step, cct_min, cct_max, cct_step]);
                        res.json({ processedData }); 
                        console.log(processedData) 
                    
                    } catch (error) {
                        res.status(500).json({ error: error }); 
                    }
                } else {
                    console.log("Input CCT max is Null or Invalid");
                    res.status(400).alert("Input CCT max is Null or Invalid");
                }    
            } else {
                console.log("Input CCT min is Null or Invalid");
                res.status(400).alert("Input CCT min is Null or Invalid");
            }     
        } else {
            console.log("Input Bri max is Null or Invalid");
            res.status(400).alert("Input Bri max is Null or Invalid");
        }
    } else {
        console.log("Input Bri min is Null or Invalid");
        res.status(400).alert("Input Bri min is Null or Invalid");
    } 
})

/// ==================================================== Metrics.html ======================================================================= ///

app.get('/metrics', (req, res)=>{
    res.sendFile(__dirname + '/html/metrics.html')
})

/// ==================================================== Visual Metrics ======================================================================== ///
app.get('/visual', (req, res)=>{
    res.sendFile(__dirname + '/html/set.html')
})

// --- GET desired CCT --- //
app.post('/getCCT_OL', async function(req, res) {
    var cct = req.body.data;

    if (cct != "" && cct >= 2500 && cct <= 6500) {
        console.log('Target CCT: ', cct)    
        try {
            const processedData = await executePython('python/Open_loop(CCT).py', [cct]);
            res.json({ processedData }); 
            console.log(processedData)

        } catch (error) {
            res.status(500).json({ error: error }); 
        }
    } else {
        console.log("Input CCT is Null or Invalid");
        res.status(400).alert("Input is Null or Invalid");
    }
});

app.post('/getCCT_CL', async function(req, res) {
    var cct = req.body.data;
    console.log('Target CCT CL: ', cct) 

    try {
        const processedData = await executePython('python/P_Controller(CCT).py', [cct]);
        res.json({ processedData }); 
        console.log(processedData)

    } catch (error) {
        res.status(500).json({ error: error }); 
    }
});

// --- GET desired Plux --- //
app.post("/getPlux_OL", async function(req, res){
    var plux = req.body.data;

    if (plux != "" && plux >= 0 && plux <= 250){
        console.log("Target Plux: ", plux);
        try {
            const processedData = await executePython('python/Open_loop(Plux).py', [plux]);
            res.json({ processedData }); 
            console.log(processedData)

        } catch (error) {
            res.status(500).json({ error: error }); 
        }
    } else {
        console.log("Input Plux is Null or Invalid");
        res.status(400).alert("Input is Null or Invalid");
    }
})

app.post("/getPlux_CL", async function(req, res){
    plux =  req.body.data;
    console.log("Target Plux CL: ", plux);

    try {
        const processedData = await executePython('python/P_Controller(Plux).py', [plux]);
        res.json({ processedData }); 
        console.log(processedData)

    } catch (error) {
        res.status(500).json({ error: error }); 
    }
})

// --- GET desired CRI --- //
app.post("/getCRI_OL", async function(req, res){
    var cri = req.body.data;

    if (cri != "" && cri >= 0 && cri <=100){
        console.log("Target CRI: ", cri);
        try {
            const processedData = await executePython('python/Open_loop(CRI).py', [cri]);
            res.json({ processedData }); 
            console.log(processedData)

        } catch (error) {
            res.status(500).json({ error: error }); 
        }
    } else {
        console.log("Input CRI is Null or Invalid");
        res.status(400).alert("Input is Null or Invalid");
    }
})

app.post("/getCRI_CL", async function(req, res){
    var cri = req.body.data;
    console.log("Target CRI CL: ", cri);

    try {
        const processedData = await executePython('python/P_Controller(CRI).py', [cri]);
        res.json({ processedData }); 
        console.log(processedData)

    } catch (error) {
        res.status(500).json({ error: error }); 
    }
})

/// ==================================================== Non Visual Metrics ======================================================================== ///

// --- GET desired MEDI & MDER --- //
// Open loop 
app.post("/getMEDI_MDER_OL", async function(req, res) { 
    var medi = req.body.inputmedi;
    var mder = req.body.inputmder;

    if (medi != "" && medi >= 0 && medi <= 200) {
        console.log("Target MEDI: " + medi);
        if(mder != "" && mder >=0 && mder <= 1){
            console.log("Target MDER: " + mder);
            try {
                const processedData = await executePython('python/Open_loop(Medi_Mder).py', [medi, mder]);
                res.json({ processedData }); 
                console.log(processedData)
            } catch (error) {
                res.status(500).json({ error: error }); 
            }
        } else {
            console.log("Input MDER is Null or Invalid");
            res.status(400).alert("Input MDER is Null or Invalid");
        }
    } else {
        console.log("Input MEDI is Null or Invalid");
        res.status(400).alert("Input MEDI is Null or Invalid");
    }
});

// Close loop
app.post("/getMEDI_MDER_CL", async function(req, res) { 
    var medi = req.body.inputmedi;
    var mder = req.body.inputmder;

    console.log("Target MEDI CL: " + medi);
    console.log("Target MDER CL: " + mder);

    try {
        const processedData = await executePython('python/P_Controller(Medi_Mder).py', [medi, mder]);
        res.json({ processedData }); 
        console.log(processedData)

    } catch (error) {
        res.status(500).json({ error: error }); 
    }
});

/// ==================================================== Pair Metrics ======================================================================== ///

// --- GET desired CCT & Plux --- //
// Open Loop 
app.post("/get_CCT_Plux_OL", async function(req, res){
    var cct = req.body.inputcct;
    var plux = req.body.inputplux;

    if (cct != "" && cct >= 2500 && cct <= 6500){
        console.log("Target CCT: " + cct);
        if(plux != "" && plux >= 0 && plux <= 300 ){
            console.log("Target Plux: " + plux);
            try {
                const processedData = await executePython('python/Open_loop(CCT_PLux).py', [cct, plux]);
                res.json({ processedData }); 
                console.log(processedData) 
            } catch (error) {
                res.status(500).json({ error: error }); 
            }
        } else {
            console.log("Input Plux is Null or Invalid");
            res.status(400).alert("Input Plux is Null or Invalid");
        }
    } else {
        console.log("Input CCT is Null or Invalid");
        res.status(400).alert("Input CCT is Null or Invalid");
    } 
})

// Close Loop 
app.post("/get_CCT_Plux_CL", async function(req, res){
    var cct = req.body.inputcct;
    var plux = req.body.inputplux;

    console.log("Target CCT CL: " + cct);
    console.log("Target Plux CL: " + plux)

    try {
        const processedData = await executePython('python/P_Controller(CCT_PLux).py', [cct, plux]);
        res.json({ processedData }); 
        console.log(processedData) 

    } catch (error) {
        res.status(500).json({ error: error }); 
    }
})


// --- GET desired CCT & Medi --- //
// Open Loop  
app.post("/get_CCT_MEDI_OL", async function(req, res){
    var cct = req.body.inputcct;
    var medi = req.body.inputmedi;

    if (cct != "" && cct >= 2500 && cct <= 6500){
        console.log("Target CCT: " + cct);
        if(medi != "" && medi >= 0 && medi <= 200 ){
            console.log("Target MEDI: " + medi);
            try {
                const processedData = await executePython('python/Open_loop(CCT_Medi).py', [cct, medi]);
                res.json({ processedData }); 
                console.log(processedData) 
    
            } catch (error) {
                res.status(500).json({ error: error }); 
            }
        } else {
            console.log("Input MEDI is Null or Invalid");
            res.status(400).alert("Input MEDI is Null or Invalid");
        }
    } else {
            console.log("Input CCT is Null or Invalid");
            res.status(400).alert("Input CCT is Null or Invalid");
    } 
})

// Close Loop 
app.post("/get_CCT_MEDI_CL", async function(req,res){
    var cct = req.body.inputcct;
    var medi = req.body.inputmedi;

    console.log("Target CCT CL: " + cct);
    console.log("Target MEDI CL: " + medi);

    try {
        const processedData = await executePython('python/P_Controller(CCT_Medi).py', [cct, medi]);
        res.json({ processedData }); 
        console.log(processedData) 

    } catch (error) {
        res.status(500).json({ error: error }); 
    }
    
})

// --- GET desired Plux & Medi --- // 
// Open Loop
app.post("/get_Plux_MEDI_OL", async function(req, res){
    var plux = req.body.inputplux;
    var medi = req.body.inputmedi;

    if (plux != "" && plux >= 0 && plux <= 250){
        console.log("Target Plux: " + plux);
        if(medi != "" && medi >= 0 && medi <= 200 ){
            console.log("Target MEDI: " + medi);
            try {
                const processedData  = await executePython('python/Open_loop(Plux_Medi).py', [plux, medi]);
                res.json({ processedData }); 
                console.log(processedData)
    
            } catch (error) {
                res.status(500).json({ error: error }); 
            }
        } else {
            console.log("Input MEDI is Null or Invalid");
            res.status(400).alert("Input MEDI is Null or Invalid");
        }
    } else {
            console.log("Input Plux is Null or Invalid");
            res.status(400).alert("Input Plux is Null or Invalid");
    } 
})

// Close Loop
app.post("/get_Plux_MEDI_CL", async function(req, res){
    var plux = req.body.inputplux;
    var medi = req.body.inputmedi;

    console.log("Target Plux: " + plux);
    console.log("Target Medi: " + medi);

    try {
        const processedData  = await executePython('python/P_Controller(Plux_Medi).py', [plux, medi]);
        res.json({ processedData }); 
        console.log(processedData)

    } catch (error) {
        res.status(500).json({ error: error }); 
    }
})

/// ==================================================== Step.html ======================================================================== ///

// --- step html --- //
app.get('/step', (req, res)=>{
    res.sendFile(__dirname + '/html/step.html')
})

// --- CCT and Plux --- //
app.post('/get_step_CP', async function(req, res){
    var alltime = req.body.allocatetime;
    var inCCT = req.body.initialcct;
    var inPlux = req.body.initialplux;
    var stepcct1 = req.body.stepCCT1;
    var stepcct2 = req.body.stepCCT2;
    var stepcct3 = req.body.stepCCT3;
    var stepcct4 = req.body.stepCCT4;
    var stepcct5 = req.body.stepCCT5;
    var stepplux1 = req.body.stepPlux1;
    var stepplux2 = req.body.stepPlux2;
    var stepplux3 = req.body.stepPlux3;
    var stepplux4 = req.body.stepPlux4;
    var stepplux5 = req.body.stepPlux5;
    var steptime1 = req.body.stepTime1;
    var steptime2 = req.body.stepTime2;
    var steptime3 = req.body.stepTime3;
    var steptime4 = req.body.stepTime4;
    var steptime5 = req.body.stepTime5;

    console.log("Initial CCT: " + inCCT)
    console.log("Initial Plux: " + inPlux)

    try {
        const processedData  = await executePython('python/step_CCT_PLUX.py', [alltime, inCCT, inPlux, stepcct1, stepcct2, stepcct3, stepcct4, stepcct5, stepplux1, stepplux2, stepplux3, stepplux4, stepplux5, steptime1, steptime2, steptime3, steptime4, steptime5]);
        res.json({ processedData }); 
        console.log(processedData)

    } catch (error) {
        res.status(500).json({ error: error }); 
    }
})

// --- CCT and Medi --- //
app.post('/get_step_CM', async function(req, res){
    var alltime = req.body.allocatetime;
    var inCCT = req.body.initialcct;
    var inMedi = req.body.initialmedi;
    var stepcct1 = req.body.stepCCT1;
    var stepcct2 = req.body.stepCCT2;
    var stepcct3 = req.body.stepCCT3;
    var stepcct4 = req.body.stepCCT4;
    var stepcct5 = req.body.stepCCT5;
    var stepmedi1 = req.body.stepMedi1;
    var stepmedi2 = req.body.stepMedi2;
    var stepmedi3 = req.body.stepMedi3;
    var stepmedi4 = req.body.stepMedi4;
    var stepmedi5 = req.body.stepMedi5;
    var steptime1 = req.body.stepTime1;
    var steptime2 = req.body.stepTime2;
    var steptime3 = req.body.stepTime3;
    var steptime4 = req.body.stepTime4;
    var steptime5 = req.body.stepTime5;

    console.log("Initial CCT: " + inCCT)
    console.log("Initial Medi: " + inMedi)

    try {
        const processedData  = await executePython('python/step_CCT_Medi.py', [alltime, inCCT, inMedi, stepcct1, stepcct2, stepcct3, stepcct4, stepcct5, stepmedi1, stepmedi2, stepmedi3, stepmedi4, stepmedi5, steptime1, steptime2, steptime3, steptime4, steptime5]);
        res.json({ processedData }); 
        console.log(processedData)

    } catch (error) {
        res.status(500).json({ error: error }); 
    }
})


// --- Plux and Medi --- //
app.post('/get_step_PM', async function(req, res){
    var alltime = req.body.allocatetime;
    var inPlux = req.body.initialplux;
    var inMedi = req.body.initialmedi;
    var stepplux1 = req.body.stepPlux1;
    var stepplux2 = req.body.stepPlux2;
    var stepplux3 = req.body.stepPlux3;
    var stepplux4 = req.body.stepPlux4;
    var stepplux5 = req.body.stepPlux5;
    var stepmedi1 = req.body.stepMedi1;
    var stepmedi2 = req.body.stepMedi2;
    var stepmedi3 = req.body.stepMedi3;
    var stepmedi4 = req.body.stepMedi4;
    var stepmedi5 = req.body.stepMedi5;
    var steptime1 = req.body.stepTime1;
    var steptime2 = req.body.stepTime2;
    var steptime3 = req.body.stepTime3;
    var steptime4 = req.body.stepTime4;
    var steptime5 = req.body.stepTime5;

    
    console.log("Initial Plux: " + inPlux)
    console.log("Initial Medi: " + inMedi)

    try {
        const processedData  = await executePython('python/step_Plux_Medi.py', [alltime, inPlux, inMedi, stepplux1, stepplux2, stepplux3, stepplux4, stepplux5, stepmedi1, stepmedi2, stepmedi3, stepmedi4, stepmedi5, steptime1, steptime2, steptime3, steptime4, steptime5]);
        res.json({ processedData }); 
        console.log(processedData)

    } catch (error) {
        res.status(500).json({ error: error }); 
    }
})


// --- Medi and Mder --- //
app.post('/get_step_MM', async function(req, res){
    var alltime = req.body.allocatetime;
    var inMedi = req.body.initialmedi;
    var inMder = req.body.initialmder;
    var stepmedi1 = req.body.stepMedi1;
    var stepmedi2 = req.body.stepMedi2;
    var stepmedi3 = req.body.stepMedi3;
    var stepmedi4 = req.body.stepMedi4;
    var stepmedi5 = req.body.stepMedi5;
    var stepmder1 = req.body.stepMder1;
    var stepmder2 = req.body.stepMder2;
    var stepmder3 = req.body.stepMder3;
    var stepmder4 = req.body.stepMder4;
    var stepmder5 = req.body.stepMder5;
    var steptime1 = req.body.stepTime1;
    var steptime2 = req.body.stepTime2;
    var steptime3 = req.body.stepTime3;
    var steptime4 = req.body.stepTime4;
    var steptime5 = req.body.stepTime5;

    
    console.log("Initial Medi: " + inMedi)
    console.log("Initial Mder: " + inMder)

    try {
        const processedData  = await executePython('python/step_Medi_Mder.py', [alltime, inMedi, inMder, stepmedi1, stepmedi2, stepmedi3, stepmedi4, stepmedi5, stepmder1, stepmder2, stepmder3, stepmder4, stepmder5, steptime1, steptime2, steptime3, steptime4, steptime5]);
        res.json({ processedData }); 
        console.log(processedData)

    } catch (error) {
        res.status(500).json({ error: error }); 
    }
})



// Listen on port 3000
app.listen(port, () => console.info(`Listening on port ${port}`))







