<h2 style="text-align: center;">MMV_playground</h2>

<p style="text-align: center;"><b>Jianxu Chen</b><br>
Microscopy Machine Vision Lab (MMV-Lab)<br>
Leibniz-Institut für Analytische Wissenschaften – ISAS – e.V.<br>
Bunsen-Kirchhoff-Str. 11, 44139 Dortmund, Germany</p>


![Figure1]((https://raw.githubusercontent.com/MMV-Lab/MMV-playground/main/docs/images/figure1.png))

### Basic information:

* Plugin name: **mmv_playground**
* Important dependency: pip install aicssegmentation  (https://pypi.org/project/aicssegmentation/#description)
* Scope: for 2D microscopy image segmentation
* Use case: users open a 2D microscopy image, then try to apply different functions to obtain the best segmentation results. Note: the input to a specific function can be the raw image the user opens or the output result from another function.
* Overall layout: see the picture above. Plugin name on the top. Then, a list of 7 different functions, each as a collapsable box. When users click one box, it expands. The expanded area will contain (1) a selection box to select which image layer to be used as the input, (2) a few fields to enter parameters, the number of parameters and the type of parameters depend on each function, which are detailed below.

### Function 1:

* Name: **intensity normalization**
* Parameters:
    * Parameter 1 name: lower_percentage
    * Parameter 1 type: float16
    * Parameter 1 value: a slider in the range of 0 to 5, incremental by 0.01

    * Parameter 2 name: upper_percentage
    * Parameter 2 type: float16
    * Parameter 2 value: a slider in the range of 95 to 100, incremental by 0.01
    ```
    import numpy as np
    lower_v = np.percentile(input_image, lower_percentage)
    upper_v = np.percentile(input_image, upper_percentage)

    img = np.clip(input_image, lower_v, upper_v)
    output = (img - lower_v) / (upper_v - lower_v)
    ```

### Function 2:

* Name: **Smoothing**
* Parameters:
    * Parameter name: "Smoothing Method:"
    * Parameter type: List of strings
    * Parameter value: ["Gaussian", "edge-preserving"]
    ```
    If selection == "Gaussian":
        # use function from scipy
        from scipy.ndimage import gaussian_filter
        output = gaussian_filter(input_image, sigma=1.0)
    elif selection == "edge-preserving":
        # use function from itk
        import itk
        itk_img = itk.GetImageFromArray(input_image.astype(np.float32))

        # set spacing
        itk_img.SetSpacing([1, 1])

        # define the filter
        gradientAnisotropicDiffusionFilter = itk.GradientAnisotropicDiffusionImageFilter.New(itk_img)
    
        gradientAnisotropicDiffusionFilter.SetNumberOfIterations(10)
        gradientAnisotropicDiffusionFilter.SetTimeStep(0.125)
        gradientAnisotropicDiffusionFilter.SetConductanceParameter(1.2)
        gradientAnisotropicDiffusionFilter.Update()
    
        # run the filter
        itk_img_smooth = gradientAnisotropicDiffusionFilter.GetOutput()

        # extract the output array
        output = itk.GetArrayFromImage(itk_img_smooth)
    ```

### Function 3:

* Name: **Background correction**
* Parameters:
    * parameter name: kernel_size
    * parameter type: integer 8
    * parameter value: a slider in the range of 1 to 100, incremental by 1
    ```
    from skimage.morphology import white_tophat
    from skimage.morphology import disk

    output = white_tophat(input_image, disk(kernel_size))
    ```

### Function 4:

* Name: **spot-shape filter**
* Parameters:
    * Parameter name: sigma
    * Parameter type: float16
    * Parameter value: a slider in the range of 0.5 to 10, incremental by 0.5
    ```
    from scipy.ndimage import gaussian_laplace
    output = -1 * (sigma**2) * gaussian_laplace(input_image, sigma)
    ```

### Function 5:

* Name: **filament-shape filter**
* Parameters:
    * Parameter name: sigma
    * Parameter type: float16
    * Parameter value: a slider in the range of 0.25 to 5, incremental by 0.25
    ```
    From aicssegmentation.core.vessel import vesselness2D
    output = vesselness2D(input_image, sigmas=[sigma])
    ```

### Function 6:

* Name: **Thresholding**
* Parameters:
    * Parameter name: threshold method
    * Parameter type: list of strings
    * Parameter value: ["Otsu", "Li", "Triangle", "Sauvola"]
    ```
    from skimage.filters import threshold_ sauvola
    from from skimage.filters import threshold_li
    from from skimage.filters import threshold_triangle
    If selection == "Otsu":
        from skimage.filters import threshold_otsu
        t_otsu = threshold_otsu(input_image)
        output = input_image > t_otsu
    elif selection == "Li":
        from skimage.filters import threshold_li
        t_li = threshold_li(input_image)
        output = input_image > t_li
    elif selection == "Triangle":
        from skimage.filters import threshold_triangle
        t_tri = threshold_triangle(input_image)
        output = input_image > t_tri
    elif selection == "Sauvola":
        from skimage.filters import threshold_sauvola
        t_local = threshold_ sauvola (input_image)
        output = input_image > t_local
    ```

### Function 7: 

* Name: **Topology-preserving thinning**
* Parameters:
    * Parameter 1 name: min_thickness
    * Parameter 2 name: thin
    ```
    from scipy.ndimage import distance_transform_edt
    import numpy as np
    from skimage.morphology import disk, erosion, medial_axis

    output = input_image > 0
    safe_zone = np.zeros_like(output)
    ctl = medial_axis(output >0)
    dist = distance_transform_edt(ctl == 0)
    safe_zone[zz, :, :] = dist > min_thickness + 1e-5

    rm_candidate = np.logical_xor(output, erosion(output, disk(thin)))
    output[np.logical_and(safe_zone, rm_candidate)] = 0
    ```
