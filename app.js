// http://localhost:3000/

// imports
const express = require("express");
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
        console.log(processedData)

    } catch (error) {
        res.status(500).json({ error: error }); 
    }
});
/// ==================================================== Music & Light.html ======================================================================= ///
app.get('/audio', (req, res)=>{
    res.sendFile(__dirname + '/html/music.html')
})

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

/// ==================================================== Visual.html ======================================================================== ///
app.get('/visual', (req, res)=>{
    res.sendFile(__dirname + '/html/visual.html')
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

/// ==================================================== Non Visual.html ======================================================================== ///
app.get('/nonvisual', (req, res)=>{
    res.sendFile(__dirname + '/html/non-visual.html')
})

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

/// ==================================================== Pair.html ======================================================================== ///
app.get('/pair', (req, res)=>{
    res.sendFile(__dirname + '/html/pair.html')
})

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

// Listen on port 3000
app.listen(port, () => console.info(`Listening on port ${port}`))







